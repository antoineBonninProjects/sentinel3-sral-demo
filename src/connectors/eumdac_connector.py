"""
This module provides utilities for interacting with the EUMETSAT API.

The `EumdacConnector` class allows users to authenticate with the API,
refresh tokens, and retrieve satellite data from the Copernicus program.

Classes:
    EumdacConnector -- Manages authentication and API requests with automatic token refresh.

Methods:
    - __init__: Initializes the EumdacConnector with credentials and token refresh settings.
    - load_credentials: Loads API credentials from a configuration file.
    - refresh_token: Refreshes the API token if it is close to expiration.
    - datastore: Property that returns the current DataStore instance, refreshing the token 
    if necessary.
    - save_to_zarr: Saves multiple NetCDF datasets to a partitionned Zarr collection.
    - download_products: Downloads a list of products from a specified collection.
    - _download_product: Downloads a single product and saves it as a zip file.
    - _unzip_product: Unzips a downloaded product in the specified directory.
    - _remove_zip: Removes the zip file after extraction.
    - _process_product: Orchestrates the download, unzipping, and removal of a single product.

Dependencies:
    - eumdac: External library for interacting with EUMETSAT's API.
    - configparser: For loading API credentials from a configuration file.
    - dask: For parallel processing and task scheduling.
    - fsspec: For filesystem access.
    - xarray: For handling datasets.
    - zcollection: For Zarr partitionning and easy handling.

Usage:
    Example: List SRAL related collections.

        datastore = EumdacConnector().datastore
        for collection_id in datastore.collections:
            if "SRAL" in collection_id.title:
                if "non-public" in collection_id.abstract:
                    continue
                print(f"Collection ID({collection_id}): {collection_id.title}")
"""

__all__ = ['EumdacConnector']

import configparser
from datetime import datetime, timedelta
import logging
import os
import shutil
import zipfile

import dask
from dask.distributed import Client
import eumdac
import fsspec
import xarray as xr
import zcollection

from utils.singleton import SingletonMeta
from utils.logging_utils import setup_module_logger

logger = setup_module_logger(__name__)

# Make some loggers less verbose
logging.getLogger('asyncio').setLevel(logging.INFO)
logging.getLogger('eumdac').setLevel(logging.INFO)
logging.getLogger('fsspec.local').setLevel(logging.INFO)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)


class EumdacConnector(metaclass=SingletonMeta):
    """
    Class to wrap eumetsat::eumdac connector to pull copernicus data.
    Credentials are loaded from a .ini file in ~/.eumdac.
    Class implements an auto API token refresh.
    """

    def __init__(
        self,
        credentials_filename: str = "credentials.ini",
        refresh_token_margin_mn: timedelta = timedelta(minutes=5),
    ) -> None:
        """
        :param str credentials_filename: name of your credentials file in ~/.eumdac folder
        :param timedelta refresh_token_margin_mn: margin to keep on the token expiration
        date to anticipate renewal (in minutes)
        """
        self._credentials_filename: str = credentials_filename
        self._refresh_token_margin_mn: timedelta = refresh_token_margin_mn

        self._consumer_key: str = None
        self._consumer_secret: str = None
        self._token: eumdac.token.AccessToken = None
        self._datastore: eumdac.DataStore = None

        self.load_credentials()
        self.refresh_token()

    def load_credentials(self) -> None:
        """
        Load credentials from .ini file
        """
        config_file = os.path.expanduser(f"~/.eumdac/{self._credentials_filename}")

        # Secrets are in [myprofile] section from .ini file.
        # Use RawConfigParser to diable interpolation (credentials may contain '%' chars)
        config: configparser.RawConfigParser = configparser.RawConfigParser()
        config.read(config_file)
        self._consumer_key = config.get('myprofile', 'consumer_key')
        self._consumer_secret = config.get('myprofile', 'consumer_secret')

    def refresh_token(self) -> bool:
        """
        Refreshes API token if token is close to expiration.
        Takes the _refresh_token_margin_mn into account to anticipate renewal

        :return: True if token has been refrehed, false otherwise
        :rtype: bool
        """
        is_refreshed: bool = False
        refresh_date = datetime.now() + self._refresh_token_margin_mn

        if (self._token is None) or (self._token.expiration < refresh_date):
            self._token = eumdac.AccessToken((self._consumer_key, self._consumer_secret))
            is_refreshed = True
            logger.debug(
                "Token has been refreshed and wii be valid until %s", self._token.expiration
            )

        return is_refreshed

    @property
    def datastore(self) -> None:
        """
        Gets _datastore attribute and consider token expiration
        """
        is_token_refreshed: bool = self.refresh_token()

        if self._datastore is None or is_token_refreshed:
            self._datastore = eumdac.DataStore(self._token)

        return self._datastore

    def save_to_zarr(
        self,
        netcdf_file_paths: list[str],
        zarr_base_path: str,
        zarr_partition_handler: zcollection.partitioning.Partitioning,
        time_dimension: str,
    ) -> None:
        """
        Save multiple NetCDF datasets to a Zarr collection.

        This method reads NetCDF files from the specified paths, concatenates them
        along the specified time dimension, and saves the resulting dataset into
        a Zarr collection. If the collection does not exist, it will be created.

        :param list[str] netcdf_file_paths:
            A list of file paths to the NetCDF datasets to be saved.
        :param str zarr_base_path:
            The base path where the Zarr collection will be stored.
        :param zcollection.partitioning.Partitioning zarr_partition_handler:
            The partitioning strategy to use for the Zarr collection.
        :param str time_dimension:
            The name of the dimension along which the datasets will be concatenated.

        :return: None
        :rtype: None
        """
        client = Client()

        if netcdf_file_paths == []:
            raise ValueError("netcdf_file_paths cannot be empty")

        # open all datasets
        xr_ds_list: list[xr.Dataset] = []
        logger.info("Loading every netcdf files to a xr.Dataset...")
        for dataset_file in netcdf_file_paths:
            ds: xr.Dataset = xr.open_dataset(dataset_file)
            ds.close()
            xr_ds_list.append(ds)

        # concat them along time_dimension to make  single write - index needs to be monotonic
        logger.info("Concat datasets to a single distributed xr.Dataset...")
        combined_data: xr.Dataset = xr.concat(xr_ds_list, dim=time_dimension)
        combined_data = combined_data.sortby(time_dimension)

        zds: zcollection.Dataset = zcollection.Dataset.from_xarray(combined_data)

        # Create zcollection Collection if not existing yet, otherwise use existing
        collection: zcollection.Collection = None
        try:
            collection = zcollection.open_collection(zarr_base_path, mode="w")
            logger.debug("Using existing zcollection at %s", zarr_base_path)
        except ValueError:
            # ValueError is raised if collection is not found
            logger.info("zcollection at %s not found, creating it", zarr_base_path)
            filesystem: fsspec.implementations.local.LocalFileSystem = fsspec.filesystem("file")

            collection = zcollection.create_collection(
                axis=time_dimension,
                ds=zds,
                partition_handler=zarr_partition_handler,
                partition_base_dir=zarr_base_path,
                filesystem=filesystem,
            )

        logger.info("Inserting data to the zarr collection at %s", zarr_base_path)
        collection.insert(zds)
        client.close()

    def download_products(
        self, collection_id: str, product_ids: list[str], download_dir: str
    ) -> list[str]:
        """
        Downloads a list of products from the given collection, unzips them,
        and removes the zip files.

        This method creates a download directory if it doesn't exist,
        and distributes the download, unzip, and cleanup tasks across a Dask cluster.

        :param str collection_id: The ID of the product collection to download from.
        :param list[str] product_ids: A list of product IDs to be downloaded.
        :param str download_dir: The directory where the downloaded products will be saved.
        :return: The list of downloaded folders
        :rtype: list[str]
        """
        os.makedirs(download_dir, exist_ok=True)
        products_batch = list(product_ids)

        # Compute tasks in parallel across the cluster
        client = Client()
        delayed_tasks = [
            dask.delayed(self._process_product)(collection_id, str(product), download_dir)
            for product in products_batch
        ]
        logger.info("Downloading products...")
        dask.compute(*delayed_tasks)
        client.close()

        downloaded_folders = [
            os.path.join(download_dir, product_id) for product_id in products_batch
        ]
        logger.debug("Downloaded products folders: %s", downloaded_folders)
        return downloaded_folders

    def _download_product(
        self, collection_id: str, product_id: str, download_dir: str
    ) -> tuple[str, object]:
        """
        Downloads a single product from the collection and saves it as a zip file in the
        download directory.

        :param str collection_id: The ID of the product collection to download from.
        :param str product_id: The ID of the product to be downloaded.
        :param str download_dir: The directory where the downloaded product will be saved.
        :return: The path to the downloaded zip file
        :rtype: str
        """
        selected_product = self.datastore.get_product(
            product_id=product_id, collection_id=collection_id
        )

        # Download the product
        with selected_product.open() as fsrc:
            zip_path: str = os.path.join(download_dir, fsrc.name)
            with open(zip_path, mode='wb') as fdst:
                shutil.copyfileobj(fsrc, fdst)
                logger.debug("Downloading %s", zip_path)

        return zip_path

    def _unzip_product(self, zip_path: str, product_id: str, download_dir: str) -> None:
        """
        Unzips a downloaded product in the specified directory.

        :param str zip_path: The path to the downloaded zip file.
        :param object product: The product object used to identify files within the zip archive.
        :param str download_dir: The directory where the unzipped product files will be saved.
        :return: None
        :rtype: None
        """
        unzip_dir = os.path.join(download_dir, product_id)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.startswith(product_id):
                    zip_ref.extract(file, download_dir)
                    logger.debug("Unzipping %s", file)

        return unzip_dir

    def _remove_zip(self, zip_path: str) -> None:
        """
        Removes the zip file after it has been unzipped.

        :param str zip_path: The path to the zip file to be removed.
        :return: None
        :rtype: None
        """
        os.remove(zip_path)
        logger.debug("Deleting %s", zip_path)

    def _process_product(self, collection_id: str, product_id: str, download_dir: str) -> None:
        """
        Orchestrates the download, unzip, and removal of a single product.

        :param str collection_id: The ID of the product collection.
        :param str product_id: The ID of the product to be processed.
        :param str download_dir: The directory where the product will be downloaded,
        unzipped, and processed.
        :return: None
        :rtype: None
        """
        zip_path = self._download_product(collection_id, product_id, download_dir)
        unzip_dir = self._unzip_product(zip_path, product_id, download_dir)
        self._remove_zip(zip_path)

        return unzip_dir

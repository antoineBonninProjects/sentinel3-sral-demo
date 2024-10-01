"""
This module contains the ZarrProcessor class, which provides functionality to convert
and save multiple NetCDF datasets into a partitioned (with one index dimension) Zarr collection. 
The processor also supports reading, concatenating, and filtering Zarr datasets. 
This is designed to work with distributed computing using Dask and a local file system via fsspec.

In the future, ZarrProcessor could implement methods to query zarr data and load them to xr.Dataset.

Classes:
    ZarrProcessor: A class to handle the creation and insertion of datasets into Zarr collections.

Dependencies:
    - dask
    - fsspec
    - logging
    - xarray
    - zcollection
    - utils.logging_utils
"""

import logging

import dask
import dask.distributed
import fsspec
import xarray as xr
import zcollection

from utils.logging_utils import setup_module_logger

logger: logging.Logger = setup_module_logger(__name__)


class ZarrProcessor:
    """
    A processor class that manages partitioned Zarr collections from NetCDF files.

    This class is responsible for creating a Zarr collection if it doesn't exist,
    and saving NetCDF datasets with one index dimension into the collection.
    The ZarrProcessor also manages the partitioning of datasets for efficient data
    storage and retrieval.

    In the future, ZarrProcessor could implement methods to query zarr data and
    load them to xr.Dataset.

    Attributes:
        zarr_collection_path (str): Path to the Zarr collection directory.
        partition_handler (zcollection.partitioning.Partitioning):
            A handler for managing the partitioning strategy for Zarr data.
        index_dimension (str):
            The dimension along which the datasets will be indexed (e.g., time_01).
        collection (zcollection.Collection):
            The Zarr collection object, created or opened by the processor.
    """

    def __init__(
        self,
        zarr_collection_path: str,
        partition_handler: zcollection.partitioning.Partitioning,
        index_dimension: str,
    ):
        """
        :param str zarr_collection_path:
            Path to the Zarr collection where data will be stored.
        :param zcollection.partitioning.Partitioning partition_handler:
            A partitioning handler to manage how data is partitioned in the
            Zarr collection.
        :param str index_dimension:
            The dimension (e.g., 'time') along which the data will be indexed in
            the Zarr collection.
        """
        self.zarr_collection_path: str = zarr_collection_path
        self.partition_handler: zcollection.partitioning.Partitioning = partition_handler
        self.index_dimension: str = index_dimension
        self._collection: zcollection.Collection = None

    @property
    def collection(self) -> zcollection.Collection:
        """
        property binded to _collection attribute
        :return: the _collection attribute
        :rtype: zcollection.Collection
        """
        return self._collection

    def _open_or_create_collection(
        self, zarr_data_set: zcollection.Dataset
    ) -> zcollection.Collection:
        """
        Open an existing Zarr collection or create a new one if it doesn't exist.

        This method attempts to open a Zarr collection at the specified path. If the collection
        does not exist, it creates a new one using the given partitioning handler and
        the provided dataset.

        :param zcollection.Dataset zarr_data_set:
            The dataset that will be inserted into the collection, used for the
            collection's structure.

        :return: The Zarr collection object, either opened or newly created.
        :rtype: zcollection.Collection
        """
        # Create zcollection Collection if not existing yet, otherwise use existing
        collection: zcollection.Collection = None
        try:
            collection = zcollection.open_collection(self.zarr_collection_path, mode="w")
            logger.debug("Using existing zcollection at %s", self.zarr_collection_path)
        except ValueError:
            # ValueError is raised if collection is not found
            logger.info("zcollection at %s not found, creating it", self.zarr_collection_path)
            filesystem: fsspec.implementations.local.LocalFileSystem = fsspec.filesystem("file")

            collection = zcollection.create_collection(
                axis=self.index_dimension,
                ds=zarr_data_set,
                partition_handler=self.partition_handler,
                partition_base_dir=self.zarr_collection_path,
                filesystem=filesystem,
            )

        self._collection = collection
        return collection

    def netcdf_2_zarr(self, netcdf_file_paths: list[str]) -> None:
        """
        Save multiple NetCDF datasets to a Zarr collection.

        This method reads NetCDF files from the specified paths, concatenates them
        along the ZarrProcessor index_dimension, and saves the resulting dataset into
        a Zarr collection.

        :param list[str] netcdf_file_paths:
            A list of file paths to the NetCDF datasets to be saved.

        :return: None
        :rtype: None
        """

        # Use a local cluster, and threads only
        cluster: dask.distributed.LocalCluster = dask.distributed.LocalCluster(processes=False)
        client: dask.distributed.Client = dask.distributed.Client(cluster)

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
        combined_data: xr.Dataset = xr.concat(xr_ds_list, dim=self.index_dimension)
        combined_data = combined_data.sortby(self.index_dimension)

        zds: zcollection.Dataset = zcollection.Dataset.from_xarray(combined_data)

        collection: zcollection.Collection = self._open_or_create_collection(zds)

        logger.info("Inserting data to the zarr collection at %s", self.zarr_collection_path)
        collection.insert(zds)

        client.close()
        cluster.close()

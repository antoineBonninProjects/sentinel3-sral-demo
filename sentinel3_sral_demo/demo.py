"""
The main for this project.
Follow README.md to setup your env.

Run this script with:
> python -m sentinel3_sral_demo.demo
"""

import os
import zcollection

from src.connectors.eumdac_connector import EumdacConnector
from utils.opensearch_query_formatter import OpenSearchQueryFormatter


SEN3_SRAL_LVL2_COLLECTION_ID = "EO:EUM:DAT:0415"
DOWNLOAD_DIR: str = "/tmp/products"
MEASUREMENTS_FILENAME: str = "reduced_measurement.nc"
ZARR_BASE_PATH: str = "/tmp/sen3_sral"
TIME_DIMENSION: str = "time_01"
download_dir: str = os.path.join(os.getcwd(), DOWNLOAD_DIR)

if __name__ == "__main__":
    connector: EumdacConnector = EumdacConnector()
    datastore: EumdacConnector.datastore = connector.datastore

    # Query a few data files for Sentinel3A and 3B SRAL (Level2 data) for 2024-09-20
    opensearch_query = OpenSearchQueryFormatter(
        query_params={
            "pi": SEN3_SRAL_LVL2_COLLECTION_ID,
            "dtstart": "2024-09-23T00:20:00Z",
            "dtend": "2024-09-25T00:10:00Z",
        }
    ).format()
    products = datastore.opensearch(query=opensearch_query)
    product_ids = [str(x) for x in products]

    # Download files - benefits of dask parallelization
    downloaded_folders = connector.download_products(
        SEN3_SRAL_LVL2_COLLECTION_ID, product_ids, download_dir
    )

    # Store files to partitionned zarr files
    # Partition by day (with zcollection) - to be tuned depending on data use / volumetry
    netcdf_file_paths: str = [
        os.path.join(folder, MEASUREMENTS_FILENAME) for folder in downloaded_folders
    ]
    partition_handler = zcollection.partitioning.Date((TIME_DIMENSION,), resolution='D')
    connector.save_to_zarr(
        netcdf_file_paths, ZARR_BASE_PATH, partition_handler, time_dimension=TIME_DIMENSION
    )

"""
Main entry point for the Sentinel3-SRAL project.

This script facilitates the downloading and processing of satellite product data from 
the EUMDAC API. Follow the setup instructions outlined in the `README.md` file to 
configure the environment.

.. note::

    The following environment variables are used by the script, along with their 
    default values:

    +-----------------------+-----------------------+-------------------------------------+
    | Variable Name         | Default Value         | Description                         |
    +-----------------------+-----------------------+-------------------------------------+
    | LOG_LEVEL             | INFO                  | Sets the logging level for the      |
    |                       |                       | application.                        |
    +-----------------------+-----------------------+-------------------------------------+
    | COLLECTION_ID         | EO:EUM:DAT:0415       | Specifies the product collection    |
    |                       |                       | to query.                           |
    +-----------------------+-----------------------+-------------------------------------+
    | DOWNLOAD_DIR          | /tmp/products         | Directory where downloaded products |
    |                       |                       | will be stored.                     |
    +-----------------------+-----------------------+-------------------------------------+
    | MEASUREMENTS_FILENAME | reduced_measurement.nc| Name of the NetCDF file to extract  |
    |                       |                       | from the downloaded ZIP.            |
    +-----------------------+-----------------------+-------------------------------------+
    | ZARR_BASE_PATH        | /tmp/sen3_sral        | Base path for persisting data to    |
    |                       |                       | a Zarr collection.                  |
    +-----------------------+-----------------------+-------------------------------------+
    | INDEX_DIMENSION       | time_01               | Dimension along which the data will |
    |                       |                       | be partitioned.                     |
    +-----------------------+-----------------------+-------------------------------------+

Functionality
-------------

1. **Product Querying**: Queries the EUMDAC API for products within the specified 
   `COLLECTION_ID` using a predefined OpenSearch query.

2. **Data Downloading**: For each product that matches the filters, downloads the 
   data to the `DOWNLOAD_DIR`. Extracts the NetCDF file named 
   `MEASUREMENTS_FILENAME` from the downloaded ZIP files.

3. **Data Processing**: Constructs a dataset from all downloaded data. Persists 
   the dataset to a Zarr collection located at `ZARR_BASE_PATH`, partitioned along 
   the specified `INDEX_DIMENSION`.

4. **Dask Integration**: Utilizes Dask for distributed processing, both for 
   downloading and executing basic xarray operations. Configured in LocalCluster 
   mode with threading for efficiency.

Future Enhancements
--------------------

Future releases will introduce a checkpointing mechanism, allowing the script to 
automatically download new files based on the latest available data, rather than 
relying on a hardcoded date range.

Usage
-----

To run this script, execute the following command:

.. code-block:: bash

    python -m tasks.persist_sen3_sral_data_to_zarr
"""

import logging
import os
import zcollection

import eumdac.product
from src.connectors.eumdac_connector import EumdacConnector
from src.processors.zarr_processor import ZarrProcessor
from utils.logging_utils import setup_root_logging, setup_module_logger
from utils.opensearch_query_formatter import OpenSearchQueryFormatter

setup_root_logging()

logger: logging.Logger = setup_module_logger(__name__)

COLLECTION_ID: str = os.getenv("COLLECTION_ID", "EO:EUM:DAT:0415")
DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/products")
MEASUREMENTS_FILENAME: str = os.getenv("MEASUREMENTS_FILENAME", "reduced_measurement.nc")
ZARR_BASE_PATH: str = os.getenv("ZARR_BASE_PATH", "/tmp/sen3_sral")
INDEX_DIMENSION: str = os.getenv("INDEX_DIMENSION", "time_01")
download_dir: str = os.path.join(os.getcwd(), DOWNLOAD_DIR)

if __name__ == "__main__":
    logger.info("Connecting EUMDAC datastore...")
    connector: EumdacConnector = EumdacConnector()
    datastore: eumdac.datastore.DataStore = connector.datastore

    # Query a few data files for Sentinel3A and 3B SRAL (Level2 data) for 2024-09-20
    opensearch_query: str = OpenSearchQueryFormatter(
        query_params={
            "pi": COLLECTION_ID,
            "dtstart": "2024-09-23T00:20:00Z",
            "dtend": "2024-09-25T00:10:00Z",
        }
    ).format()
    logger.info("Listing EUMDAC products matching filters '%s'", opensearch_query)
    products: eumdac.product.Product = datastore.opensearch(query=opensearch_query)
    product_ids: list[str] = [str(x) for x in products]
    # If in local mode, process only a subset of the products for faster execution
    if os.getenv("LOCAL_MODE", "1"):
        logger.info("Local mode: processing every 50th product to debug faster")
        product_ids = product_ids[::50]
    logger.info("%s matching products found", len(product_ids))
    logger.debug("Listed products are: %s", product_ids)

    # Download files - benefits of dask parallelization
    logger.info("Downloading products (dask parallelized)...")
    downloaded_folders: list[str] = connector.download_products(
        COLLECTION_ID, product_ids, download_dir, MEASUREMENTS_FILENAME
    )

    # Store files to partitionned zarr files
    # Partition by day (with zcollection) - to be tuned depending on data use / volumetry
    logger.info("Persisting data in a partitionned zarr collection...")
    netcdf_file_paths: list[str] = [
        os.path.join(folder, MEASUREMENTS_FILENAME) for folder in downloaded_folders
    ]
    partition_handler: zcollection.partitioning.Partitioning = zcollection.partitioning.Date(
        (INDEX_DIMENSION,), resolution='M'
    )

    zarr_processor: ZarrProcessor = ZarrProcessor(
        ZARR_BASE_PATH, partition_handler, index_dimension=INDEX_DIMENSION
    )
    zarr_processor.netcdf_2_zarr(netcdf_file_paths)
    logger.info("Job done")

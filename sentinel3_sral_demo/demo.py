"""
The main for this project.
Follow README.md to setup your env.

Run this script with:
> python -m sentinel3_sral_demo.demo
"""

from src.connectors.eumdac_connector import EumdacConnector
from utils.opensearch_query_formatter import OpenSearchQueryFormatter


SEN3_SRAL_LVL2_COLLECTION_ID = "EO:EUM:DAT:0415"

if __name__ == "__main__":
    datastore = EumdacConnector().datastore

    # Query a few data files for Sentinel3A and 3B SRAL (Level2 data) for 2024-09-20
    opensearch_query = OpenSearchQueryFormatter(
        query_params={
            "pi": SEN3_SRAL_LVL2_COLLECTION_ID,
            "dtstart": "2024-09-20T00:00:00Z",
            "dtend": "2024-09-20T00:10:00Z",
        }
    ).format()
    products = datastore.opensearch(query=opensearch_query)
    print(products)

    for product in products:
        print(product)

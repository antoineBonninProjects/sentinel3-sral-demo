"""
The main for this project.
Follow README.md to setup your env.

Run this script with:
> python -m sentinel3_sral_demo.demo
"""

from src.connectors.eumdac_connector import EumdacConnector

SEN3A_SRAL_LVL2_COLLECTION_ID = "EO:EUM:DAT:0415"

if __name__ == "__main__":
    datastore = EumdacConnector().datastore

    products = datastore.opensearch(query=f'pi={SEN3A_SRAL_LVL2_COLLECTION_ID}')
    print(products)

    for product in products:
        print(product)
        break

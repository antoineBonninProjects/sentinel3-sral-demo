"""
The main for this project.
Follow README.md to setup your env.

Run this script with:
> python -m sentinel3_sral_demo.demo
"""

from src.connectors.eumdac_connector import EumdacConnector

if __name__ == "__main__":
    datastore = EumdacConnector().datastore
    for collection_id in datastore.collections:
        if "SRAL" in collection_id.title:
            if "non-public" in collection_id.abstract:
                continue
            print(f"Collection ID({collection_id}): {collection_id.title}")

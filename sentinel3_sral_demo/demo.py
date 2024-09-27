"""
The main for this project.
Follow README.md to setup your env.

Run this script with:
> python -m sentinel3_sral_demo.demo
"""

from src.connectors.eumdac_connector import EumdacConnector

if __name__ == "__main__":
    eudmac_connector = EumdacConnector()

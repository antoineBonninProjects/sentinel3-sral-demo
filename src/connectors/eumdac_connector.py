"""
This module provides utilities for interacting with the EUMETSAT API.

The `EumdacConnector` class allows users to authenticate with the API,
refresh tokens, and retrieve satellite data from the Copernicus program.

Classes:
    EumdacConnector -- Manages authentication and API requests with automatic token refresh.
    
Functions:
    - N/A

Dependencies:
    - eumdac: External library for interacting with EUMETSAT's API.
    - configparser: For loading API credentials from a configuration file.

Usage:
    Example:
        connector = EumdacConnector()
"""

import configparser
from datetime import datetime, timedelta
import os

import eumdac

from utils.singleton import SingletonMeta


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
    ):
        """
        :param str credentials_filename: name of your credentials file in ~/.eumdac folder
        :param timedelta refresh_token_margin_mn: margin to keep on the token expiration
        date to anticipate renewal (in minutes)
        """
        self._credentials_filename = credentials_filename
        self._refresh_token_margin_mn = refresh_token_margin_mn

        self._consumer_key: str = None
        self._consumer_secret: str = None
        self._token: eumdac.token.AccessToken = None
        self.datastore: eumdac.DataStore = None

        self.load_credentials()
        self.refresh_token()

    def load_credentials(self):
        """
        Load credentials from .ini file
        """
        config_file = os.path.expanduser(f"~/.eumdac/{self._credentials_filename}")

        # Secrets are in [myprofile] section from .ini file.
        # Use RawConfigParser to diable interpolation (credentials may contain '%' chars)
        config = configparser.RawConfigParser()
        config.read(config_file)
        self._consumer_key = config.get('myprofile', 'consumer_key')
        self._consumer_secret = config.get('myprofile', 'consumer_secret')

    def refresh_token(self):
        """
        Refreshes API token if token is close to expiration.
        Takes the _refresh_token_margin_mn into account to anticipate renewal
        """
        refresh_date = datetime.now() + self._refresh_token_margin_mn

        if (self._token is None) or (self._token.expiration < refresh_date):
            self._token = eumdac.AccessToken((self._consumer_key, self._consumer_secret))

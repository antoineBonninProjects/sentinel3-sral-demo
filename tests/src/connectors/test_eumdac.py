# pylint: skip-file
"""
Test for module src.connectors.eumdac_connector

"""

from datetime import (
    datetime,
    timedelta,
)

import pytest

from src.connectors.eumdac_connector import EumdacConnector


# Mock eumdac.token.AccessToken class
class MockAccessToken:
    def __init__(self, credentials):
        self.credentials = credentials
        self.expiration = datetime.now() + timedelta(hours=1)  # Mock a token valid for 1 hour


@pytest.fixture
def mock_config(mocker):
    # Mock the configparser to return specific consumer key/secret
    mocker.patch("configparser.RawConfigParser.read", return_value=None)
    mock_config = mocker.patch("configparser.RawConfigParser.get")
    mock_config.side_effect = lambda section, key: {
        'consumer_key': 'mocked_consumer_key',
        'consumer_secret': 'mocked_consumer_secret',
    }[key]


@pytest.fixture
def mock_token(mocker):
    # Mock the eumdac AccessToken creation
    mocker.patch("eumdac.AccessToken", side_effect=MockAccessToken)


@pytest.fixture
def connector(mock_config, mock_token):
    # Initialize the EumdacConnector with mocked dependencies
    return EumdacConnector(credentials_filename="credentials.ini")


def test_load_credentials(connector):
    """
    Test that credentials are loaded correctly from the .ini file
    """
    assert connector._consumer_key == "mocked_consumer_key"
    assert connector._consumer_secret == "mocked_consumer_secret"


def test_token_refresh(connector):
    """
    Test that the token is refreshed correctly
    """
    assert connector._token is not None
    assert isinstance(connector._token, MockAccessToken)
    assert connector._token.credentials == ('mocked_consumer_key', 'mocked_consumer_secret')
    assert connector._token.expiration > datetime.now()


def test_token_refresh_with_margin(connector):
    """
    Test that the token is refreshed based on the expiration margin
    """
    # Simulate that the token is close to expiration by adjusting _refresh_token_margin_mn
    connector.refresh_token_margin_mn = timedelta(minutes=59)
    connector.refresh_token()  # Refresh token based on the new margin

    # Assert that the token is refreshed even with a valid margin
    assert connector._token is not None
    assert isinstance(connector._token, MockAccessToken)


def test_token_not_refreshed_if_still_valid(mocker, connector):
    """
    Test that the token is NOT refreshed when it is still valid and far from expiration.
    """
    # Mock eumdac.AccessToken and track calls
    mock_access_token = mocker.patch("eumdac.AccessToken", side_effect=MockAccessToken)

    # Simulate a token with more than enough time before expiration
    connector._token.expiration = datetime.now() + timedelta(hours=2)

    # Refresh the token (but it shouldn't refresh since token is still valid)
    connector.refresh_token()
    mock_access_token.assert_not_called()

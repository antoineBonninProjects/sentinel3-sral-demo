# pylint: skip-file
"""
Test for module src.connectors.eumdac_connector

"""

from datetime import (
    datetime,
    timedelta,
)

import os
import pytest
import tempfile
import shutil
from unittest import mock
import zipfile

from src.connectors.eumdac_connector import EumdacConnector


# Mock eumdac.token.AccessToken and eumdac.DataStore classes
class MockAccessToken:
    def __init__(self, credentials):
        self.credentials = credentials
        self.expiration = datetime.now() + timedelta(hours=1)  # Mock a token valid for 1 hour


class MockDataStore:
    def __init__(self, token):
        self.token = token

    def get_product(self, product_id, collection_id):
        # Return a mocked product
        return MockProduct(name='product.zip')


# Mock eumdac product
class MockProduct:
    def __init__(self, name):
        self.name = name

    def open(self):
        pass


# Your existing fixtures
@pytest.fixture
def mock_config(mocker):
    mocker.patch("configparser.RawConfigParser.read", return_value=None)
    mock_config = mocker.patch("configparser.RawConfigParser.get")
    mock_config.side_effect = lambda section, key: {
        'consumer_key': 'mocked_consumer_key',
        'consumer_secret': 'mocked_consumer_secret',
    }[key]


@pytest.fixture
def mock_token(mocker):
    mocker.patch("eumdac.AccessToken", side_effect=MockAccessToken)


@pytest.fixture
def mock_datastore(mocker):
    mocker.patch("eumdac.DataStore", side_effect=MockDataStore)


@pytest.fixture
def connector(mock_config, mock_token, mock_datastore):
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
    Test that the token is refreshed correctly on EumdacConnector init
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


def test_refresh_token_not_expired(connector):
    """
    Test that the token is not refreshed if it's not expired.
    """
    connector.refresh_token()  # First refresh to set the token
    assert connector.refresh_token() is False  # No refresh should occur
    assert connector._token.credentials == ("mocked_consumer_key", "mocked_consumer_secret")


def test_refresh_token_expired(connector):
    """
    Test that the token is refreshed if it's close to expiration.
    """
    connector._token.expiration = datetime.now() - timedelta(minutes=1)  # Force expiration
    assert connector.refresh_token() is True  # Token should be refreshed
    assert connector._token.credentials == ("mocked_consumer_key", "mocked_consumer_secret")


def test_datastore_property(connector):
    """
    Test that accessing the datastore property refreshes the token if needed.
    """
    assert connector.datastore is not None
    assert isinstance(connector.datastore, MockDataStore)


def test_datastore_refresh_token(connector):
    """
    Test that accessing the datastore refreshes the token when needed.
    """
    connector._token.expiration = datetime.now() - timedelta(minutes=1)  # Force expiration
    datastore = connector.datastore
    assert isinstance(datastore, MockDataStore)
    assert datastore.token.credentials == ("mocked_consumer_key", "mocked_consumer_secret")


def test_download_products(connector, mocker):
    """
    Test the download_products method.
    """
    mocker.patch('os.makedirs')
    mocker.patch('dask.delayed', return_value=mocker.Mock())
    mocker.patch('dask.compute')

    collection_id = "collection1"
    product_ids = [f"product{x}" for x in range(100)]
    download_dir = "downloads"

    downloaded_folders = connector.download_products(collection_id, product_ids, download_dir)

    # Assert the correct folder structure is returned
    assert downloaded_folders == [f"downloads/product{x}" for x in range(100)]


def test_download_product(connector):
    """
    Test the download_product. For now it only tests that we open the Product object and that
    shutil.copyfileobj() is called. Test is a bit light.
    Note: Complete this test
    """
    download_dir = tempfile.mkdtemp()  # Create a temporary download directory
    collection_id = 'collection123'
    product_id = 'product456'

    # Simulate a temporary file for the product to be downloaded
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b'Test product content.')
    temp_file.close()

    # Patch the open method used within the function to simulate product download
    with mock.patch('builtins.open', mock.mock_open()) as mocked_open:
        with mock.patch('shutil.copyfileobj') as mock_copy:
            # Mock the file open behavior for the MockProduct
            with mock.patch.object(MockProduct, 'open', return_value=open(temp_file.name, 'rb')):
                # Call the _download_product method on the connector
                result = connector._download_product(collection_id, product_id, download_dir)

                # Expected zip path
                expected_zip_path = os.path.join(download_dir, 'product.zip')

                # Assertions
                mocked_open.assert_called()  # Check the file is opened for writing
                mock_copy.assert_called_once()  # Ensure the copyfileobj was called

    # Clean up
    shutil.rmtree(download_dir)  # Remove the temporary download directory
    os.remove(temp_file.name)


def test_unzip_product(connector, mocker):
    """
    Test the _unzip_product method.
    - Test to unzip a zip containing the measurement_filename
    - Test to unzip a zip not containing the measurement_filename
    """
    zip_path = "./file.zip"
    product_id = "product1"
    download_dir = "downloads"

    # Create a dummy zip file for testing
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        zip_file.writestr(f"{product_id}/file.txt", b"Sample content")

    # Verify the file has been extracted, when measurement_filename is found
    connector._unzip_product(zip_path, product_id, download_dir, measurements_filename="file.txt")
    extracted_path = os.path.join(download_dir, product_id, 'file.txt')
    assert os.path.exists(extracted_path)
    os.remove(extracted_path)  # cleanup

    # Verify the file has not been extracted, when measurement_filename is found
    connector._unzip_product(
        zip_path, product_id, download_dir, measurements_filename="unexisting_file.txt"
    )
    extracted_path = os.path.join(download_dir, product_id, 'unexisting_file.txt')
    assert not os.path.exists(extracted_path)

    # Clean up
    os.remove(zip_path)


def test_remove_zip(connector, mocker):
    """
    Test the _remove_zip method.
    """
    zip_path = "./file.zip"

    # Create a dummy zip file for testing
    with open(zip_path, 'w') as f:
        f.write('test')

    connector._remove_zip(zip_path)

    # Verify the file has been removed
    assert not os.path.exists(zip_path)


def test_process_product(connector, mocker):
    """
    Test the _process_product method.
    - check private methods are called
    - check default measurements_filename value
    - check override default measurements_filename value
    """
    mocker.patch.object(connector, '_download_product', return_value="./file.zip")
    mocker.patch.object(connector, '_unzip_product', return_value="./unzipped")
    mocker.patch.object(connector, '_remove_zip')

    collection_id = "collection1"
    product_id = "product1"
    download_dir = "downloads"

    # Check that all steps were called, with default measurements_filename
    result = connector._process_product(collection_id, product_id, download_dir)
    connector._download_product.assert_called_once_with(collection_id, product_id, download_dir)
    connector._unzip_product.assert_called_once_with(
        "./file.zip", product_id, download_dir, 'reduced_measurement.nc'
    )
    connector._remove_zip.assert_called_once_with("./file.zip")

    # prepare next sub test: reset mock counters
    connector._download_product.reset_mock()
    connector._unzip_product.reset_mock()
    connector._remove_zip.reset_mock()

    # Check that all steps were called, with overriden measurements_filename
    result = connector._process_product(
        collection_id, product_id, download_dir, measurements_filename='other.nc'
    )
    connector._download_product.assert_called_once_with(collection_id, product_id, download_dir)
    connector._unzip_product.assert_called_once_with(
        "./file.zip", product_id, download_dir, 'other.nc'
    )
    connector._remove_zip.assert_called_once_with("./file.zip")

    assert result == "./unzipped"

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
from unittest import mock
import xarray as xr
import zcollection
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
def mock_datastore(mocker):
    # Mock the eumdac DataStore creation
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


@pytest.fixture
def setup_zarr_test(mocker):
    """Fixture to set up mock datasets and related behavior."""
    mock_ds1 = mocker.Mock(spec=xr.Dataset)
    mock_ds2 = mocker.Mock(spec=xr.Dataset)
    mocker.patch('xarray.open_dataset', side_effect=[mock_ds1, mock_ds2])

    mock_zarr_ds = mocker.Mock(spec=zcollection.Dataset)
    mocker.patch('zcollection.Dataset.from_xarray', return_value=mock_zarr_ds)

    mock_collection = mock.Mock()
    mocker.patch('zcollection.open_collection', return_value=mock_collection)

    mock_combined_ds = mock.Mock(spec=xr.Dataset)
    mocker.patch('xarray.concat', return_value=mock_combined_ds)

    return mock_ds1, mock_ds2, mock_zarr_ds, mock_collection, mock_combined_ds


def test_save_to_zarr_nominal(connector, setup_zarr_test):
    """
    Test the save_to_zarr method.
    """
    netcdf_file_paths = ["file1.nc", "file2.nc"]
    zarr_base_path = "path/to/zarr"
    zarr_partition_handler = mock.Mock()
    time_dimension = "time"

    # Call the method under test
    connector.save_to_zarr(
        netcdf_file_paths, zarr_base_path, zarr_partition_handler, time_dimension
    )

    # Ensure both datasets were opened
    xr.open_dataset.assert_called()
    assert xr.open_dataset.call_count == 2

    # Dataset is combined and sorted
    mock_combined_ds = setup_zarr_test[4]
    zcollection.Dataset.from_xarray.assert_called_once_with(mock_combined_ds.sortby())

    # Check that the collection methods were called correctly
    mock_collection = setup_zarr_test[3]
    mock_zarr_ds = setup_zarr_test[2]
    mock_collection.insert.assert_called_once_with(mock_zarr_ds)

    # Check if concat was called with correct parameters
    assert xr.concat.call_count == 1
    assert xr.concat.call_args[0][0] == list(setup_zarr_test[:2])  # mock_ds1, mock_ds2
    assert xr.concat.call_args[1] == {'dim': time_dimension}


def test_save_to_zarr_no_netcdf_files(connector):
    """
    Test behavior when no NetCDF files are provided.
    """
    netcdf_file_paths = []
    zarr_base_path = "path/to/zarr"
    zarr_partition_handler = mock.Mock()
    time_dimension = "time"

    with pytest.raises(ValueError, match="netcdf_file_paths cannot be empty"):
        connector.save_to_zarr(
            netcdf_file_paths, zarr_base_path, zarr_partition_handler, time_dimension
        )


def test_save_to_zarr_collection_already_exists(connector, mocker, setup_zarr_test):
    """
    Test behavior when the Zarr collection already exists.
    """
    netcdf_file_paths = ["file1.nc", "file2.nc"]
    zarr_base_path = "path/to/zarr"
    zarr_partition_handler = mock.Mock()
    time_dimension = "time"

    mocker.patch('zcollection.open_collection', side_effect=ValueError("Collection not found"))
    mock_create_collection = mocker.patch(
        'zcollection.create_collection', return_value=mocker.Mock()
    )

    connector.save_to_zarr(
        netcdf_file_paths, zarr_base_path, zarr_partition_handler, time_dimension
    )

    # Assert that create_collection was called
    mock_create_collection.assert_called_once()


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


def test_unzip_product(connector, mocker):
    """
    Test the _unzip_product method.
    """
    zip_path = "./file.zip"
    product_id = "product1"
    download_dir = "downloads"

    # Create a dummy zip file for testing
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        zip_file.writestr(f"{product_id}/file.txt", b"Sample content")

    connector._unzip_product(zip_path, product_id, download_dir)

    # Verify the file has been extracted
    extracted_path = os.path.join(download_dir, product_id, 'file.txt')
    assert os.path.exists(extracted_path)

    # Clean up
    os.remove(zip_path)
    os.remove(extracted_path)


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
    """
    mocker.patch.object(connector, '_download_product', return_value="./file.zip")
    mocker.patch.object(connector, '_unzip_product', return_value="./unzipped")
    mocker.patch.object(connector, '_remove_zip')

    collection_id = "collection1"
    product_id = "product1"
    download_dir = "downloads"

    result = connector._process_product(collection_id, product_id, download_dir)

    # Check that all steps were called
    connector._download_product.assert_called_once_with(collection_id, product_id, download_dir)
    connector._unzip_product.assert_called_once_with("./file.zip", product_id, download_dir)
    connector._remove_zip.assert_called_once_with("./file.zip")

    assert result == "./unzipped"

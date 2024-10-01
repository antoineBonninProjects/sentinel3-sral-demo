# pylint: skip-file
"""
Test for module src.processors.zarr_processor

"""

import pytest
import xarray as xr
import zcollection
from unittest import mock

from src.processors.zarr_processor import ZarrProcessor


@pytest.fixture
def processor():
    # Initialize the ZarrProcessor
    zarr_collection_path = "/path/to/zarr"
    zarr_partition_handler = mock.Mock()
    index_dimension = "time"
    return ZarrProcessor(zarr_collection_path, zarr_partition_handler, index_dimension)


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


def test_save_to_zarr_nominal(processor, setup_zarr_test):
    """
    Test the save_to_zarr method.
    """
    netcdf_file_paths = ["file1.nc", "file2.nc"]

    # Call the method under test
    processor.netcdf_2_zarr(netcdf_file_paths)

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
    assert xr.concat.call_args[1] == {'dim': processor.index_dimension}


def test_save_to_zarr_no_netcdf_files(processor):
    """
    Test behavior when no NetCDF files are provided.
    """
    netcdf_file_paths = []
    zarr_base_path = "path/to/zarr"
    zarr_partition_handler = mock.Mock()
    time_dimension = "time"

    with pytest.raises(ValueError, match="netcdf_file_paths cannot be empty"):
        processor.netcdf_2_zarr(netcdf_file_paths)


def test_save_to_zarr_collection_already_exists(processor, mocker, setup_zarr_test):
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

    processor.netcdf_2_zarr(netcdf_file_paths)

    # Assert that create_collection was called
    mock_create_collection.assert_called_once()

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
    mock_ds1 = mocker.MagicMock(spec=xr.Dataset)
    mock_ds2 = mocker.MagicMock(spec=xr.Dataset)
    mocker.patch('xarray.open_dataset', side_effect=[mock_ds1, mock_ds2])

    # Setup the mock datasets to return specific variables
    mock_ds1.__getitem__.side_effect = lambda key: (
        mocker.Mock(
            spec=xr.Dataset,
            data_vars={
                k: v
                for k, v in {'var1': [1, 2, 3], 'var2': [4, 5, 6], 'var3': [7, 8, 9]}.items()
                if k in key
            },
        )
    )

    mock_ds2.__getitem__.side_effect = lambda key: (
        mocker.Mock(
            spec=xr.Dataset,
            data_vars={
                k: v
                for k, v in {
                    'var1': [10, 20, 30],
                    'var2': [40, 50, 60],
                    'var3': [70, 80, 90],
                }.items()
                if k in key
            },
        )
    )

    mock_zarr_ds = mocker.Mock(spec=zcollection.Dataset)
    mocker.patch('zcollection.Dataset.from_xarray', return_value=mock_zarr_ds)

    mock_collection = mock.Mock()
    mocker.patch('zcollection.open_collection', return_value=mock_collection)

    mock_combined_ds = mock.Mock(spec=xr.Dataset)
    mocker.patch('xarray.concat', return_value=mock_combined_ds)

    return mock_ds1, mock_ds2, mock_zarr_ds, mock_collection, mock_combined_ds


def test_collection_property(processor):
    """
    Test that getter on the _collection property.
    """
    assert processor.collection is None


@mock.patch("zcollection.create_collection")
@mock.patch("zcollection.open_collection")
def test_open_or_create_collection_existing_collection(
    mock_open_collection, mock_create_collection, processor
):
    """
    Test the case where the collection already exists.
    """
    # Mock the zcollection open_collection function to return a collection object
    mock_collection = mock.Mock(spec=zcollection.Collection)
    mock_open_collection.return_value = mock_collection

    # Call the _open_or_create_collection method
    dataset = mock.Mock(spec=zcollection.Dataset)
    collection = processor._open_or_create_collection(dataset)

    # Assert that open_collection was called with the correct arguments
    mock_open_collection.assert_called_once_with("/path/to/zarr", mode="w")

    # Assert that create_collection was never called (since collection already exists)
    mock_create_collection.assert_not_called()

    # Assert that the collection returned is the mocked one
    assert collection == mock_collection


@mock.patch("zcollection.create_collection")
@mock.patch(
    "zcollection.open_collection", side_effect=ValueError
)  # Simulate ValueError when collection not found
@mock.patch("fsspec.filesystem")
def test_open_or_create_collection_new_collection(
    mock_fsspec, mock_open_collection, mock_create_collection, processor
):
    """
    Test the case where the collection does not exist and is created.
    """
    # Mock the zcollection create_collection function to return a collection object
    mock_new_collection = mock.Mock(spec=zcollection.Collection)
    mock_create_collection.return_value = mock_new_collection

    # Call the _open_or_create_collection method
    dataset = mock.Mock(spec=zcollection.Dataset)
    collection = processor._open_or_create_collection(dataset)

    # Assert that open_collection was called and raised a ValueError
    mock_open_collection.assert_called_once_with("/path/to/zarr", mode="w")

    # Assert that create_collection was called with the right arguments
    mock_create_collection.assert_called_once_with(
        axis="time",
        ds=dataset,
        partition_handler=processor.partition_handler,
        partition_base_dir="/path/to/zarr",
        filesystem=mock_fsspec.return_value,
    )


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
    mock_collection.insert.assert_called_once_with(mock_zarr_ds, chunk_size=(5000,))

    # Check if concat was called with correct parameters
    assert xr.concat.call_count == 1
    assert xr.concat.call_args[0][0] == list(setup_zarr_test[:2])  # mock_ds1, mock_ds2
    assert xr.concat.call_args[1] == {'dim': processor.index_dimension}

    assert processor.collection is not None


def test_save_to_zarr_select_variables(processor, setup_zarr_test):
    """
    Test the save_to_zarr method with a few variables specified
    """
    netcdf_file_paths = ["file1.nc", "file2.nc"]

    # Call the method under test
    processor.netcdf_2_zarr(netcdf_file_paths, variables=["var1"])

    # Ensure both datasets were opened
    xr.open_dataset.assert_called()
    assert xr.open_dataset.call_count == 2

    # Dataset is combined and sorted
    mock_combined_ds = setup_zarr_test[4]
    zcollection.Dataset.from_xarray.assert_called_once_with(mock_combined_ds.sortby())

    # Check that the collection methods were called correctly
    mock_collection = setup_zarr_test[3]
    mock_zarr_ds = setup_zarr_test[2]
    mock_collection.insert.assert_called_once_with(mock_zarr_ds, chunk_size=(5000,))


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

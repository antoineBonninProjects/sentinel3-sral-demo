# pylint: skip-file
"""
Test for module utils.logging_utils
"""
import os
import logging
from unittest.mock import patch
import pytest
import socket
from utils.logging_utils import (
    _ContextFilter,
    setup_root_logging,
    setup_module_logger,
    _list_my_loggers,
)


@pytest.fixture
def logger_with_filter():
    """
    Fixture to set up a logger with the ContextFilter.
    """
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(ip)s - %(message)s')
    handler.setFormatter(formatter)

    ctx_filter = _ContextFilter()
    handler.addFilter(ctx_filter)

    logger.addHandler(handler)

    return logger


def test_context_filter_ip(logger_with_filter, monkeypatch):
    """
    Test that the ContextFilter sets the correct IP in the log record.
    """

    test_ip = '192.168.1.1'

    def mock_gethostbyname(hostname):
        return test_ip

    monkeypatch.setattr(socket, 'gethostbyname', mock_gethostbyname)

    # Create a log record
    record = logger_with_filter.makeRecord(
        'test_logger', logging.INFO, 'test_file.py', 10, 'This is a test message.', None, None
    )

    assert logger_with_filter.handlers[0].filters[0].filter(record) is True
    assert record.ip == test_ip


def test_setup_root_logging_no_env_var():
    """
    Test root logging setup when environment variable LOG_LEVEL is not set.
    """
    if 'LOG_LEVEL' in os.environ:
        del os.environ['LOG_LEVEL']

    setup_root_logging()

    logger = logging.getLogger()
    assert logger.level == logging.INFO  # Default level should be INFO
    assert len(logger.handlers) == 2  # file and console handlers


def test_setup_root_logging_with_env_var():
    """
    Test root logging setup when environment variable LOG_LEVEL is set.
    """
    os.environ['LOG_LEVEL'] = 'DEBUG'
    setup_root_logging()

    logger = logging.getLogger()
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2


def test_setup_module_logger_with_none_log_level():
    """
    Test module logger setup with log_level set to None.
    """
    os.environ['LOG_LEVEL'] = 'WARNING'

    setup_root_logging()
    module_logger = setup_module_logger('my_module', log_level=None)

    assert module_logger.level == logging.WARNING
    assert module_logger.name == 'my_module'


def test_setup_module_logger_with_specified_log_level():
    """
    Test module logger setup with a specific log_level.
    """
    setup_root_logging()
    module_logger = setup_module_logger('my_module', log_level=logging.ERROR)

    assert module_logger.level == logging.ERROR
    assert module_logger.name == 'my_module'


def test_import_module_before_setup_root_logging():
    """
    Test module import before calling setup_root_logging.
    Imported module logger handlers are re-configured in setup_module_logger.
    """
    os.environ['LOG_LEVEL'] = 'DEBUG'

    # Set up the module logger before root logger setup
    module_logger = setup_module_logger('src.module2', logging.ERROR)
    assert module_logger.level == logging.ERROR
    assert len(module_logger.handlers) == 0

    # configure the root logger
    setup_root_logging()

    # Check that the logger's name and level remain unchanged
    assert module_logger.name == 'src.module2'
    assert module_logger.level == logging.ERROR  # Level should remain ERROR

    # handlers should now be added
    assert len(module_logger.handlers) == 2

    # Verify that the correct handlers are assigned
    for handler in module_logger.handlers:
        assert isinstance(handler, logging.FileHandler) or isinstance(
            handler, logging.StreamHandler
        )


def test_list_my_loggers():
    """
    Test the _list_my_loggers function.
    Make sure only loggers with prefixes in logging_utils.MY_MODULES_PREFIX_LIST
    are returned by _list_my_loggers.
    """
    setup_root_logging()

    logging.getLogger('src.module1')
    logging.getLogger('utils.module2')
    logging.getLogger('external_lib.module')  # This should not be included

    loggers = _list_my_loggers()
    assert 'src.module1' in loggers
    assert 'utils.module2' in loggers
    assert 'external_lib.module' not in loggers

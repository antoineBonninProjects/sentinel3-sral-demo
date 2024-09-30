"""
A utility module for setting up logging configurations with optional log rotation.
This module allows for both file-based logging with rotation and console logging,
making it suitable for various applications.

Dependencies:
- logging
- os
- logging.handlers.TimedRotatingFileHandler
"""

__all__ = ["setup_root_logging", "setup_module_logger"]

import logging
import os
from logging.handlers import TimedRotatingFileHandler

MY_MODULES_PREFIX_LIST = ["src", "utils"]


def _list_my_loggers() -> list[str]:
    """
    List all loggers that are defined in the application modules,
    specifically those that start with prefixes defined in MY_MODULES_PREFIX_LIST.

    The prefixes currently used are "src" and "utils".

    :return: A list of logger names that belong to the application modules.
    :rtype: list[str]
    """

    # Get all loggers from the logger manager
    logger_dict = logging.Logger.manager.loggerDict

    # List loggers derived from the root logger that match the specified prefixes
    own_module_loggers = [
        name
        for name, logger in logger_dict.items()
        if (
            isinstance(logger, logging.Logger)
            and any(name.startswith(prefix) for prefix in MY_MODULES_PREFIX_LIST)
        )
    ]

    return own_module_loggers


def setup_root_logging(log_file='/tmp/app.log', when='midnight', backup_count=5) -> None:
    """
    Set up the root logging configuration with time-based log rotation.

    This function initializes the logging system for the root logger to log messages
    to a specified file with time-based rotation and to the console. It creates the
    log file's directory if it does not exist, sets the logging level, and formats
    the log messages.

    This function also resets all custom modules handlers so that they use root loggers handlers.
    This is useful if we import a module before calling 'setup_root_logging()', because module
    logger is defined at module level and hence does not benefit from root logger configs.
    We could first call 'setup_root_logging()' and then import modules, but this violates
    pylint C0413 (imports should be made before code is executed).

    :param log_file: The name of the log file to write logs to (default: 'app.log').
    :param when: The time interval for log rotation (default: 'midnight').
                 Options include 'S' for seconds, 'M' for minutes, 'H' for hours,
                 'D' for days, 'midnight' for midnight.
    :param backup_count: The number of backup log files to keep (default: 5).
                         Older log files will be deleted once this limit is exceeded.
    """
    # Default to the value of env variable LOG_LEVEL, or INFO if env variable not set
    default_log_level_str: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    default_log_level: int = getattr(logging, default_log_level_str, logging.INFO)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Set up the handlers, formatters, log level
    handler: logging.FileHandler = TimedRotatingFileHandler(
        log_file, when=when, backupCount=backup_count
    )
    formatter: logging.Formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Set up the root logger
    logger: logging.Logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(default_log_level)
    logger.addHandler(handler)

    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(default_log_level)  # Use the same default level for console
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Modules who have been imported before root handler setup, have a logger
    # defined prior to root logger setup. So we have to update them to make sure
    # they use root logger handlers too.
    my_loggers = [logging.getLogger(x) for x in _list_my_loggers()]
    for my_logger in my_loggers:
        # Delete existing handlers and add root logger handlers
        for h in my_logger.handlers:
            my_logger.removeHandler(h)
        my_logger.addHandler(handler)
        my_logger.addHandler(console_handler)
        # Do not propagate to avoid duplicate logs
        my_logger.propagate = False


def setup_module_logger(module_name: str, log_level: int = None) -> logging.Logger:
    """
    Set up a logger for a specific module with a customizable logging level.

    This function creates a logger for the specified module name, sets its logging
    level, and inherits handlers and formatter from the root logger.

    :param module_name: The name of the module for which to create the logger.
    :param level: The logging level to set for the module logger.
                  Default to None, means we use env variable 'LOG_LEVEL' instead.
                  Options include logging.[DEBUG|INFO|WARNING|ERROR].
    :return: The configured logger for the specified module.
    """

    # Default to the value of env variable LOG_LEVEL, or INFO if env variable not set
    default_log_level_str: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    default_log_level: int = getattr(logging, default_log_level_str, logging.INFO)

    # Create a logger for the specified module
    logger = logging.getLogger(module_name)

    # Set the logging level
    log_level = log_level if log_level else default_log_level
    logger.setLevel(log_level)

    return logger

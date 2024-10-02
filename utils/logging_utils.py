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
from logging.handlers import TimedRotatingFileHandler
import os
import socket
from typing import Optional

MY_MODULES_PREFIX_LIST: list[str] = ["src", "utils"]


def _list_my_loggers() -> list[str]:
    """
    List all loggers that are defined in the application modules,
    specifically those that start with prefixes defined in MY_MODULES_PREFIX_LIST.

    The prefixes currently used are "src" and "utils".

    :return: A list of logger names that belong to the application modules.
    :rtype: list[str]
    """

    # Get all loggers from the logger manager
    logger_dict: dict = logging.Logger.manager.loggerDict

    # List loggers derived from the root logger that match the specified prefixes
    own_module_loggers: list[str] = [
        name
        for name, logger in logger_dict.items()
        if (
            isinstance(logger, logging.Logger)
            and any(name.startswith(prefix) for prefix in MY_MODULES_PREFIX_LIST)
        )
    ]

    return own_module_loggers


class _ContextFilter(logging.Filter):
    """
    Custom filter to dynamically set IP address to logs.
    Based on: https://docs.python.org/3/howto/logging-cookbook.html#filters-contextual

    Relies on logging.Filter.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Does not filter any log. Instead, it gets the IP of the node running the
        code and exposes it for the Logger Formatter.

        :param logging.LogRecord record: the log record to update with IP address info
        :return: True - it is a passing filter
        :rtype: bool
        """
        record.ip = self.get_ip()
        return True

    def get_ip(self) -> str:
        """
        Returns the IP address of the node running the code.

        :return: IP address as a string.
        :rtype: str
        """
        return socket.gethostbyname(socket.gethostname())


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

    # Set up ContextFilter
    ctx_filter: _ContextFilter = _ContextFilter()

    # Set up the handlers, formatters, log level
    handler: logging.FileHandler = TimedRotatingFileHandler(
        log_file, when=when, backupCount=backup_count
    )
    formatter: logging.Formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d %(levelname)-8s | %(ip)s PID:%(process)d TID:%(thread)d '
        '| %(name)s %(funcName)s %(filename)s:%(lineno)3s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    handler.setFormatter(formatter)
    handler.addFilter(ctx_filter)

    # Set up the root logger
    logger: logging.Logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(default_log_level)
    logger.addHandler(handler)

    # Set up console logging
    console_handler: logging.Handler = logging.StreamHandler()
    console_handler.setLevel(default_log_level)  # Use the same default level for console
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Modules who have been imported before root handler setup, have a logger
    # defined prior to root logger setup. So we have to update them to make sure
    # they use root logger handlers too.
    my_loggers: list[logging.Logger] = [logging.getLogger(x) for x in _list_my_loggers()]
    for my_logger in my_loggers:
        # Delete existing handlers and add root logger handlers
        for h in my_logger.handlers:
            my_logger.removeHandler(h)
        my_logger.addHandler(handler)
        my_logger.addHandler(console_handler)
        # Do not propagate to avoid duplicate logs
        my_logger.propagate = False


def setup_module_logger(module_name: str, log_level: Optional[int] = None) -> logging.Logger:
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
    logger: logging.Logger = logging.getLogger(module_name)

    # Set the logging level
    module_log_level: int = log_level if log_level else default_log_level
    logger.setLevel(module_log_level)

    return logger

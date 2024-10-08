"""
This module provides utilities for formatting query parameters into a URL-encoded string 
suitable for OpenSearch queries.

The `OpenSearchQueryFormatter` class takes a dictionary of query parameters and converts them 
into a URL-encoded query string.

Classes:
    OpenSearchQueryFormatter -- Formats query parameters into a URL-encoded string for OpenSearch.

Usage:
    Example:
        formatter = OpenSearchQueryFormatter({"q": "test", "size": 10})
        query_string = formatter.format()  # Returns "q=test&size=10"
"""

__all__ = ['OpenSearchQueryFormatter']

import logging
from .logging_utils import setup_module_logger

logger: logging.Logger = setup_module_logger(__name__)


class OpenSearchQueryFormatter:
    """
    A class used to format query parameters for OpenSearch into a URL-encoded string.

    This formatter takes a dictionary of query parameters and converts them into a properly
    formatted query string, suitable for OpenSearch.

    Example usage:
        formatter = OpenSearchQueryFormatter({"q": "test", "size": 10})
        query_string = formatter.format()  # Returns "q=test&size=10"

    """

    def __init__(self, query_params: dict) -> None:
        """
        Initializes the OpenSearchQueryFormatter with a dictionary of query parameters.

        :param query_params: A dictionary where the keys are parameter names and values are
        the corresponding values to be used in the query string.
        :type query_params: dict
        """
        if not isinstance(query_params, dict):
            raise ValueError("query_params must be a dict")
        self._query_params: dict = query_params
        self._formatted_query: str | None = None

    @property
    def formatted_query(self):
        """
        Property to expose _formatted_query attribute. Represents the query in opensearch format.
        """
        return self._formatted_query

    def format(self) -> str:
        """
        Formats the query parameters into a URL-encoded query string.

        :return: The URL-encoded query string formatted from the dictionary.
        :rtype: str

        :example:
            If `_query_params` is `{"q": "search", "size": 20}`, the result would be:
            "q=search&size=20"
        """
        self._formatted_query = "&".join([f"{k}={v}" for k, v in self._query_params.items()])
        logger.debug(self._formatted_query)
        return self._formatted_query

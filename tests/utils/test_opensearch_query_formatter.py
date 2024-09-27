# pylint: skip-file
"""
Test for module utils.opensearch_query_formatter
"""
from utils.opensearch_query_formatter import OpenSearchQueryFormatter


def test_format_single_query_param():
    """
    Test formatting with a single query parameter.
    """
    formatter = OpenSearchQueryFormatter({"q": "test"})
    assert formatter.format() == "q=test"


def test_format_multiple_query_params():
    """
    Test formatting with multiple query parameters.
    """
    formatter = OpenSearchQueryFormatter({"q": "search", "size": 10, "sort": "desc"})
    assert formatter.format() == "q=search&size=10&sort=desc"


def test_format_empty_query_params():
    """
    Test formatting with empty query parameters.
    """
    formatter = OpenSearchQueryFormatter({})
    assert formatter.format() == ""


def test_format_query_params_with_special_chars():
    """
    Test formatting with special characters in query parameters.
    """
    formatter = OpenSearchQueryFormatter({"q": "test & trial", "size": 10})
    assert formatter.format() == "q=test & trial&size=10"


def test_format_query_params_with_numbers():
    """
    Test formatting with numbers as values.
    """
    formatter = OpenSearchQueryFormatter({"page": 2, "size": 50})
    assert formatter.format() == "page=2&size=50"


def test_format_query_params_with_booleans():
    """
    Test formatting with boolean values.
    """
    formatter = OpenSearchQueryFormatter({"is_active": True, "has_items": False})
    assert formatter.format() == "is_active=True&has_items=False"


def test_format_query_params_with_mixed_types():
    """
    Test formatting with mixed data types in query parameters.
    """
    formatter = OpenSearchQueryFormatter({"q": "test", "page": 2, "enabled": True})
    assert formatter.format() == "q=test&page=2&enabled=True"

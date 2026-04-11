"""Unit tests for aragora/utils/sql_helpers.py."""

from __future__ import annotations

from aragora.utils.sql_helpers import _escape_like_pattern, escape_like_pattern


class TestEscapeLikePattern:
    def test_plain_string_unchanged(self):
        assert escape_like_pattern("hello world") == "hello world"

    def test_escapes_percent(self):
        assert escape_like_pattern("100%") == "100\\%"

    def test_escapes_underscore(self):
        assert escape_like_pattern("test_value") == "test\\_value"

    def test_escapes_backslash(self):
        assert escape_like_pattern("folder\\name") == "folder\\\\name"

    def test_escapes_all_special_chars(self):
        result = escape_like_pattern("100%_match\\path")
        assert result == "100\\%\\_match\\\\path"

    def test_empty_string(self):
        assert escape_like_pattern("") == ""

    def test_multiple_percents(self):
        assert escape_like_pattern("%%") == "\\%\\%"

    def test_multiple_underscores(self):
        assert escape_like_pattern("__init__") == "\\_\\_init\\_\\_"

    def test_backslash_before_percent(self):
        assert escape_like_pattern("\\%") == "\\\\\\%"

    def test_only_special_chars(self):
        assert escape_like_pattern("%_\\") == "\\%\\_\\\\"

    def test_alias_is_same_function(self):
        assert _escape_like_pattern is escape_like_pattern

    def test_unicode_passthrough(self):
        assert escape_like_pattern("café résumé") == "café résumé"

    def test_mixed_content(self):
        result = escape_like_pattern("SELECT * FROM t WHERE x=100%")
        assert result == "SELECT * FROM t WHERE x=100\\%"

"""Tests for aragora.markets.repo_guard (AGT-04 SD-7).

Flag gating, allowlist semantics, wildcard mode, fail-closed behaviour,
from_env construction, require_allowed error messages.  No network calls.
"""

from __future__ import annotations

import pytest

from aragora.markets.repo_guard import (
    RepoVisibilityError,
    RepoVisibilityGuard,
    _ALLOWLIST_VAR,
    _FLAG,
)


class TestFlagGating:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_FLAG, raising=False)
        monkeypatch.delenv(_ALLOWLIST_VAR, raising=False)
        assert not RepoVisibilityGuard.from_env().enabled

    @pytest.mark.parametrize("val", ["1", "true", "yes", "on"])
    def test_truthy_values_enable(self, val: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_FLAG, val)
        monkeypatch.setenv(_ALLOWLIST_VAR, "owner/repo")
        assert RepoVisibilityGuard.from_env().enabled

    @pytest.mark.parametrize("val", ["0", "false", ""])
    def test_falsy_values_disable(self, val: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_FLAG, val)
        assert not RepoVisibilityGuard.from_env().enabled

    def test_flag_off_any_repo_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_FLAG, raising=False)
        guard = RepoVisibilityGuard.from_env()
        assert guard.is_allowed("private-org/secret-repo")

    def test_flag_off_require_allowed_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_FLAG, raising=False)
        RepoVisibilityGuard.from_env().require_allowed("any/repo")  # must not raise


class TestAllowlist:
    def test_listed_repo_is_allowed(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"synaptent/aragora"}))
        assert guard.is_allowed("synaptent/aragora")

    def test_comparison_is_case_insensitive(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"owner/repo"}))
        assert guard.is_allowed("Owner/Repo")

    def test_unlisted_repo_denied(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"owner/repo"}))
        assert not guard.is_allowed("other/project")

    def test_empty_allowlist_denies_all(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset())
        assert not guard.is_allowed("any/repo")

    def test_multiple_repos_in_allowlist(self) -> None:
        guard = RepoVisibilityGuard(
            enabled=True, allowlist=frozenset({"owner/repo-a", "owner/repo-b"})
        )
        assert guard.is_allowed("owner/repo-a")
        assert guard.is_allowed("owner/repo-b")
        assert not guard.is_allowed("owner/repo-c")


class TestWildcardMode:
    def test_wildcard_allows_valid_owner_slash_repo(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"*"}))
        assert guard.is_allowed("any-org/any-repo")
        assert guard.is_allowed("synaptent/aragora")

    def test_wildcard_rejects_missing_slash(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"*"}))
        assert not guard.is_allowed("not-a-valid-repo-format")

    def test_wildcard_rejects_bare_slash_or_empty_component(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"*"}))
        assert not guard.is_allowed("owner/")
        assert not guard.is_allowed("/repo")


class TestRequireAllowed:
    def test_raises_for_unlisted_repo(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"other/repo"}))
        with pytest.raises(RepoVisibilityError, match="owner/repo"):
            guard.require_allowed("owner/repo")

    def test_raises_fail_closed_message_on_empty_allowlist(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset())
        with pytest.raises(RepoVisibilityError, match="fail-closed"):
            guard.require_allowed("any/repo")

    def test_no_raise_for_listed_repo(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"owner/repo"}))
        guard.require_allowed("owner/repo")  # must not raise

    def test_no_raise_for_wildcard_valid_repo(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"*"}))
        guard.require_allowed("any-org/any-project")  # must not raise

    def test_raises_for_wildcard_invalid_format(self) -> None:
        guard = RepoVisibilityGuard(enabled=True, allowlist=frozenset({"*"}))
        with pytest.raises(RepoVisibilityError):
            guard.require_allowed("not-a-repo")


class TestFromEnv:
    def test_reads_allowlist_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_FLAG, "1")
        monkeypatch.setenv(_ALLOWLIST_VAR, "owner/repo-a, owner/repo-b")
        guard = RepoVisibilityGuard.from_env()
        assert guard.is_allowed("owner/repo-a")
        assert not guard.is_allowed("owner/repo-c")

    def test_empty_allowlist_env_denies_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_FLAG, "1")
        monkeypatch.delenv(_ALLOWLIST_VAR, raising=False)
        assert not RepoVisibilityGuard.from_env().is_allowed("any/repo")

    def test_wildcard_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_FLAG, "1")
        monkeypatch.setenv(_ALLOWLIST_VAR, "*")
        guard = RepoVisibilityGuard.from_env()
        assert guard.is_allowed("any-org/any-project")
        assert not guard.is_allowed("bad-format")

"""Tests for the AGT-03 Phase 2 Manifold bet adapter (write path)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, date
from typing import Callable

import pytest

from aragora.connectors.prediction_markets.manifold import (
    DEFAULT_PER_DAY_CAP_MANA,
    DEFAULT_PER_MARKET_CAP_MANA,
    MANIFOLD_WRITE_FLAG,
    ManifoldBetAdapter,
    ManifoldBetResult,
    ManifoldError,
    manifold_write_enabled,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_payload(
    market_id: str = "mkt_1",
    *,
    total_liquidity: int | None = 2000,
) -> str:
    payload: dict = {
        "id": market_id,
        "slug": f"slug-{market_id}",
        "question": f"Will {market_id} happen?",
        "creatorUsername": "alice",
        "createdTime": 1_700_000_000_000,
        "closeTime": 1_800_000_000_000,
        "resolution": None,
        "isResolved": False,
        "outcomeType": "BINARY",
    }
    if total_liquidity is not None:
        payload["totalLiquidity"] = total_liquidity
    return json.dumps(payload)


def _stub(responses: dict) -> Callable[..., tuple[int, str]]:
    """HTTP stub keyed by (method_upper, url_suffix) → (status, body)."""

    def client(method: str, url: str, headers: dict, body: str | None = None) -> tuple[int, str]:
        for (m, suffix), (status, resp) in responses.items():
            if m.upper() == method.upper() and url.endswith(suffix):
                return (status, resp)
        return (404, json.dumps({"error": f"no stub for {method} {url}"}))

    return client


def _adapter(responses: dict, monkeypatch, **kwargs) -> ManifoldBetAdapter:
    monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
    return ManifoldBetAdapter(
        http_client=_stub(responses),
        api_key="test-key",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# manifold_write_enabled()
# ---------------------------------------------------------------------------


class TestManifoldWriteEnabled:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(MANIFOLD_WRITE_FLAG, raising=False)
        assert manifold_write_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_values_enable(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, value)
        assert manifold_write_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_falsy_values_stay_disabled(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, value)
        assert manifold_write_enabled() is False


# ---------------------------------------------------------------------------
# Write-path gating
# ---------------------------------------------------------------------------


class TestWriteGating:
    def test_place_bet_raises_when_flag_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(MANIFOLD_WRITE_FLAG, raising=False)
        adapter = ManifoldBetAdapter(
            http_client=lambda *a, **kw: (200, "{}"),
            api_key="k",
        )
        with pytest.raises(ManifoldError, match="disabled"):
            adapter.place_bet("mkt_1", probability=0.6, stake_mana=10)


# ---------------------------------------------------------------------------
# Cap enforcement
# ---------------------------------------------------------------------------


class TestCapEnforcement:
    def test_per_market_cap_blocks_excess(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("m1", total_liquidity=10_000)
        bet_resp = json.dumps({"id": "b1"})
        a = _adapter(
            {("GET", "market/m1"): (200, mkt), ("POST", "bet"): (200, bet_resp)},
            monkeypatch,
            per_market_cap_mana=50,
            per_day_cap_mana=500,
        )
        a.place_bet("m1", probability=0.5, stake_mana=50)
        with pytest.raises(ManifoldError, match="per-market cap"):
            a.place_bet("m1", probability=0.5, stake_mana=1)

    def test_per_day_cap_blocks_cross_market_excess(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mkt1 = _market_payload("m1", total_liquidity=10_000)
        mkt2 = _market_payload("m2", total_liquidity=10_000)
        bet_resp = json.dumps({"id": "b1"})
        a = _adapter(
            {
                ("GET", "market/m1"): (200, mkt1),
                ("GET", "market/m2"): (200, mkt2),
                ("POST", "bet"): (200, bet_resp),
            },
            monkeypatch,
            per_market_cap_mana=60,
            per_day_cap_mana=100,
        )
        a.place_bet("m1", probability=0.5, stake_mana=60)
        with pytest.raises(ManifoldError, match="per-day cap"):
            a.place_bet("m2", probability=0.5, stake_mana=50)

    def test_liquidity_fraction_cap_blocks_large_stake(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 100 mana liquidity → 5% cap = 5 mana max
        mkt = _market_payload("m_tiny", total_liquidity=100)
        a = _adapter(
            {("GET", "market/m_tiny"): (200, mkt)},
            monkeypatch,
            per_market_cap_mana=1000,
            per_day_cap_mana=10_000,
        )
        with pytest.raises(ManifoldError, match="liquidity fraction"):
            a.place_bet("m_tiny", probability=0.5, stake_mana=10)

    def test_liquidity_cap_skipped_when_liquidity_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # totalLiquidity absent from payload → no fraction check
        mkt = _market_payload("m_noliq", total_liquidity=None)
        bet_resp = json.dumps({"id": "b_noliq"})
        a = _adapter(
            {
                ("GET", "market/m_noliq"): (200, mkt),
                ("POST", "bet"): (200, bet_resp),
            },
            monkeypatch,
            per_market_cap_mana=100,
            per_day_cap_mana=1000,
        )
        # Should not raise — no liquidity data means fraction cap is skipped
        result = a.place_bet("m_noliq", probability=0.5, stake_mana=50)
        assert result.bet_id == "b_noliq"


# ---------------------------------------------------------------------------
# Successful place_bet
# ---------------------------------------------------------------------------


class TestPlaceBetSuccess:
    def test_returns_bet_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("mx", total_liquidity=5000)
        bet_resp = json.dumps({"id": "bet_abc"})
        a = _adapter(
            {("GET", "market/mx"): (200, mkt), ("POST", "bet"): (200, bet_resp)},
            monkeypatch,
        )
        r = a.place_bet("mx", probability=0.75, stake_mana=25)
        assert isinstance(r, ManifoldBetResult)
        assert r.bet_id == "bet_abc"
        assert r.market_id == "mx"
        assert r.stake_mana == 25
        assert r.probability == 0.75
        assert r.outcome == "YES"

    def test_outcome_no_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("my", total_liquidity=5000)
        bet_resp = json.dumps({"id": "bet_no"})
        a = _adapter(
            {("GET", "market/my"): (200, mkt), ("POST", "bet"): (200, bet_resp)},
            monkeypatch,
        )
        r = a.place_bet("my", probability=0.3, stake_mana=10, outcome="NO")
        assert r.outcome == "NO"

    def test_stake_counters_updated_after_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mkt = _market_payload("mz", total_liquidity=10_000)
        call_n = {"n": 0}

        def client(method: str, url: str, headers: dict, body: str | None = None):
            if method.upper() == "GET":
                return (200, mkt)
            call_n["n"] += 1
            return (200, json.dumps({"id": f"b{call_n['n']}"}))

        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
        a = ManifoldBetAdapter(
            http_client=client,
            api_key="k",
            per_market_cap_mana=200,
            per_day_cap_mana=1000,
        )
        a.place_bet("mz", probability=0.5, stake_mana=30)
        a.place_bet("mz", probability=0.6, stake_mana=30)
        assert a._market_stakes["mz"] == 60

    def test_accepts_betid_field_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("ma", total_liquidity=5000)
        # Manifold sometimes returns "betId" instead of "id"
        bet_resp = json.dumps({"betId": "bet_alias_xyz"})
        a = _adapter(
            {("GET", "market/ma"): (200, mkt), ("POST", "bet"): (200, bet_resp)},
            monkeypatch,
        )
        r = a.place_bet("ma", probability=0.5, stake_mana=10)
        assert r.bet_id == "bet_alias_xyz"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_empty_market_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
        a = ManifoldBetAdapter(http_client=lambda *a, **kw: (200, "{}"), api_key="k")
        with pytest.raises(ManifoldError, match="market_id is required"):
            a.place_bet("", probability=0.5, stake_mana=10)

    def test_probability_out_of_range_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
        a = ManifoldBetAdapter(http_client=lambda *a, **kw: (200, "{}"), api_key="k")
        for bad_prob in (0.0, 1.0, -0.1, 1.5):
            with pytest.raises(ManifoldError, match="probability"):
                a.place_bet("m", probability=bad_prob, stake_mana=10)

    def test_zero_stake_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
        a = ManifoldBetAdapter(http_client=lambda *a, **kw: (200, "{}"), api_key="k")
        with pytest.raises(ManifoldError, match="stake_mana"):
            a.place_bet("m", probability=0.5, stake_mana=0)

    def test_invalid_outcome_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MANIFOLD_WRITE_FLAG, "1")
        a = ManifoldBetAdapter(http_client=lambda *a, **kw: (200, "{}"), api_key="k")
        with pytest.raises(ManifoldError, match="outcome"):
            a.place_bet("m", probability=0.5, stake_mana=10, outcome="MAYBE")


# ---------------------------------------------------------------------------
# API error handling
# ---------------------------------------------------------------------------


class TestApiErrors:
    def test_http_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("merr", total_liquidity=5000)
        a = _adapter(
            {
                ("GET", "market/merr"): (200, mkt),
                ("POST", "bet"): (400, json.dumps({"error": "insufficient funds"})),
            },
            monkeypatch,
        )
        with pytest.raises(ManifoldError, match="HTTP 400"):
            a.place_bet("merr", probability=0.5, stake_mana=10)

    def test_missing_bet_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mkt = _market_payload("mnoid", total_liquidity=5000)
        a = _adapter(
            {
                ("GET", "market/mnoid"): (200, mkt),
                ("POST", "bet"): (200, json.dumps({"amount": 10})),
            },
            monkeypatch,
        )
        with pytest.raises(ManifoldError, match="missing"):
            a.place_bet("mnoid", probability=0.5, stake_mana=10)

    def test_stake_counters_not_updated_on_api_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mkt = _market_payload("mfail", total_liquidity=5000)
        a = _adapter(
            {
                ("GET", "market/mfail"): (200, mkt),
                ("POST", "bet"): (500, "server error"),
            },
            monkeypatch,
        )
        with pytest.raises(ManifoldError):
            a.place_bet("mfail", probability=0.5, stake_mana=10)
        # Counters must stay at zero — the bet never landed
        assert a._market_stakes.get("mfail", 0) == 0

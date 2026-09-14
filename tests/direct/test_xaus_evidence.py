"""Focused tests for the public XAUS paired-observation source mode."""

import json
from datetime import datetime, timezone

import pytest

from tests.direct.conftest import as_address, fund_and_stake, market_id, reset_known_contract


XAUS_BASE_URL = "https://xaus.com/api/v1/intraday"
XAUS_EVIDENCE_URL = "https://xaus.com/api/v1/intraday?hours=48"


def epoch(timestamp: str) -> int:
    return int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp())


def point(timestamp: str, price: str):
    return {"t": epoch(timestamp), "p": price}


def series(symbol: str, points: list[dict], *, response_symbol: str | None = None, unit: str = "troy_oz", state: str = "fresh"):
    return {
        "symbol": response_symbol or symbol,
        "hours": 48,
        "currency": "USD",
        "unit": unit,
        "interval_seconds": 120,
        "points": points,
        "coverage_seconds": 4_000,
        "data_state": {"status": state, "source": "sampler", "as_of": "2025-01-01T00:30:00Z", "age_seconds": 0},
    }


def open_xaus_market(contract, direct_vm, start="2025-01-01T00:15:00Z"):
    direct_vm.warp("2025-01-01T00:00:00Z")
    identifier = market_id(start)
    contract.open_market(identifier, start, XAUS_EVIDENCE_URL)
    return identifier


def settle_xaus(contract, direct_vm, sender, identifier, gold, silver):
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xau$",
        {"status": 200, "body": json.dumps(series("xau", gold))},
    )
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xag$",
        {"status": 200, "body": json.dumps(series("xag", silver))},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = sender
    contract.request_settlement(identifier)


@pytest.fixture
def xaus_market_contract(direct_deploy, direct_vm, direct_owner, direct_bob):
    reset_known_contract()
    contract = direct_deploy("contracts/metalswap.py")
    direct_vm.sender = direct_owner
    contract.configure_finality_gate(as_address(direct_bob))
    contract.configure_source_base_url(XAUS_BASE_URL)
    return contract


def test_xaus_both_metals_rising_uses_aligned_boundary_points(
    xaus_market_contract, direct_vm, direct_alice, direct_bob
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    fund_and_stake(xaus_market_contract, direct_vm, direct_bob, identifier, "SILVER", 100)
    settle_xaus(
        xaus_market_contract,
        direct_vm,
        direct_alice,
        identifier,
        [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "2020.000000")],
        [point("2025-01-01T00:13:02Z", "25.000000"), point("2025-01-01T00:29:02Z", "25.100000")],
    )
    detail = xaus_market_contract.get_market(identifier)
    assert detail["outcome"] == "GOLD"
    assert detail["gold_opening_timestamp"] == "2025-01-01T00:13:02Z"
    assert detail["gold_closing_timestamp"] == "2025-01-01T00:29:02Z"
    assert detail["last_reason_code"] == ""
    assert xaus_market_contract.get_protocol_config()["selection_rule"] == "latest_observation_at_or_before_boundary"


def test_xaus_both_falling_and_less_falling_metal_wins(
    xaus_market_contract, direct_vm, direct_alice, direct_bob
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    fund_and_stake(xaus_market_contract, direct_vm, direct_bob, identifier, "SILVER", 100)
    settle_xaus(
        xaus_market_contract,
        direct_vm,
        direct_alice,
        identifier,
        [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "1998.000000")],
        [point("2025-01-01T00:13:02Z", "25.000000"), point("2025-01-01T00:29:02Z", "24.750000")],
    )
    assert xaus_market_contract.get_market(identifier)["outcome"] == "GOLD"


def test_xaus_equal_percentage_returns_refund_at_different_nominal_prices(
    xaus_market_contract, direct_vm, direct_alice, direct_bob
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    fund_and_stake(xaus_market_contract, direct_vm, direct_bob, identifier, "SILVER", 100)
    settle_xaus(
        xaus_market_contract,
        direct_vm,
        direct_alice,
        identifier,
        [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "1990.000000")],
        [point("2025-01-01T00:13:02Z", "25.000000"), point("2025-01-01T00:29:02Z", "24.875000")],
    )
    detail = xaus_market_contract.get_market(identifier)
    assert detail["outcome"] == "REFUND"
    assert detail["fee_amount"] == 0
    assert detail["distributable_pool"] == 200


def test_xaus_cross_metal_timestamp_skew_is_pending(
    xaus_market_contract, direct_vm, direct_alice
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    settle_xaus(
        xaus_market_contract,
        direct_vm,
        direct_alice,
        identifier,
        [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "2020.000000")],
        [point("2025-01-01T00:12:00Z", "25.000000"), point("2025-01-01T00:29:02Z", "25.100000")],
    )
    detail = xaus_market_contract.get_market(identifier)
    assert detail["outcome"] == ""
    assert detail["settlement_state"] == "PENDING_EVIDENCE"
    assert detail["last_reason_code"] == "CONFLICTING_EVIDENCE"


def test_xaus_missing_one_of_four_boundary_points_is_pending(
    xaus_market_contract, direct_vm, direct_alice
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    settle_xaus(
        xaus_market_contract,
        direct_vm,
        direct_alice,
        identifier,
        [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "2020.000000")],
        [point("2025-01-01T00:13:02Z", "25.000000")],
    )
    detail = xaus_market_contract.get_market(identifier)
    assert detail["outcome"] == ""
    assert detail["last_reason_code"] == "EVIDENCE_NOT_AVAILABLE"


def test_xaus_stale_series_is_pending(
    xaus_market_contract, direct_vm, direct_alice
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xau$",
        {"status": 200, "body": json.dumps(series("xau", [], state="stale"))},
    )
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xag$",
        {"status": 200, "body": json.dumps(series("xag", []))},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    xaus_market_contract.request_settlement(identifier)
    assert xaus_market_contract.get_market(identifier)["last_reason_code"] == "SOURCE_UNAVAILABLE"


@pytest.mark.parametrize(
    ("response_symbol", "unit"),
    [("xag", "troy_oz"), ("xau", "ounce")],
)
def test_xaus_wrong_instrument_or_unit_is_rejected(
    xaus_market_contract, direct_vm, direct_alice, response_symbol, unit
):
    identifier = open_xaus_market(xaus_market_contract, direct_vm)
    fund_and_stake(xaus_market_contract, direct_vm, direct_alice, identifier, "GOLD", 100)
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xau$",
        {
            "status": 200,
            "body": json.dumps(
                series(
                    "xau",
                    [point("2025-01-01T00:13:02Z", "2000.000000"), point("2025-01-01T00:29:02Z", "2020.000000")],
                    response_symbol=response_symbol,
                    unit=unit,
                )
            ),
        },
    )
    direct_vm.mock_web(
        r"^https://xaus\.com/api/v1/intraday\?hours=48&symbol=xag$",
        {"status": 200, "body": json.dumps(series("xag", [point("2025-01-01T00:13:02Z", "25.000000"), point("2025-01-01T00:29:02Z", "25.100000")]))},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    xaus_market_contract.request_settlement(identifier)
    assert xaus_market_contract.get_market(identifier)["last_reason_code"] == "INVALID_SCHEMA"

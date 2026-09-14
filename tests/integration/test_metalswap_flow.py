"""Two-contract GenLayer integration coverage.

Run with a live GLSim/Studio network and an HTTPS evidence origin:

    $env:METALSWAP_INTEGRATION_SOURCE_BASE_URL = "https://<host>/evidence/"
    gltest tests/integration/test_metalswap_flow.py -v -s

The tests intentionally deploy fresh contracts so they cannot mutate the
production deployment. A complete finalized settlement test should be run
against a disposable source fixture after the market interval has elapsed.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from gltest import get_contract_factory
from gltest.accounts import get_default_account
from gltest.assertions import tx_execution_succeeded


def configured_source() -> str:
    source = os.getenv("METALSWAP_INTEGRATION_SOURCE_BASE_URL", "").strip()
    if not source:
        pytest.skip("Set METALSWAP_INTEGRATION_SOURCE_BASE_URL to run live integration coverage.")
    if not source.startswith("https://") or not source.endswith("/"):
        pytest.fail("METALSWAP_INTEGRATION_SOURCE_BASE_URL must be an HTTPS directory with a trailing slash.")
    return source


def deploy_wired_pair(source: str):
    gate = get_contract_factory("SettlementGate").deploy(args=[])
    market = get_contract_factory("MetalSwap").deploy(args=[])

    receipts = [
        gate.configure_market(args=[market.address]).transact(),
        market.configure_finality_gate(args=[gate.address]).transact(),
        market.configure_source_base_url(args=[source]).transact(),
    ]
    for receipt in receipts:
        assert tx_execution_succeeded(receipt)
    return gate, market


def open_test_market(market, source: str) -> str:
    """Open a fresh market with enough time left for the live RPC round trip."""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now.replace(minute=(now.minute // 15) * 15) + timedelta(minutes=15)
    if (start - now).total_seconds() < 120:
        start += timedelta(minutes=15)
    start_at = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    identifier = f"market-{start_at}"
    receipt = market.open_market(
        args=[identifier, start_at, f"{source}{identifier}.json"]
    ).transact()
    assert tx_execution_succeeded(receipt)
    return identifier


@pytest.mark.slow
def test_two_contract_wiring_and_position_submission():
    source = configured_source()
    gate, market = deploy_wired_pair(source)

    identifier = open_test_market(market, source)
    current = market.get_current_market(args=[]).call()
    config = market.get_protocol_config(args=[]).call()
    gate_status = gate.get_gate_status(args=[]).call()
    assert current["exists"] is True
    assert current["market_id"] == identifier
    assert current["evidence_url"].startswith(source)
    assert config["source_base_configured"] is True
    assert config["finality_gate_configured"] is True
    assert gate_status["market_configured"] is True
    assert gate_status["market_contract"].lower() == market.address.lower()

    credit_receipt = market.claim_demo_credits(args=[]).transact()
    assert tx_execution_succeeded(credit_receipt)
    position_receipt = market.place_position(
        args=[current["market_id"], "GOLD", 25]
    ).transact()
    assert tx_execution_succeeded(position_receipt)

    account = market.get_account(args=[get_default_account().address]).call()
    assert account["position_count"] == 1
    assert account["total_staked"] == 25


@pytest.mark.slow
def test_claim_is_rejected_before_market_settlement():
    source = configured_source()
    _gate, market = deploy_wired_pair(source)

    identifier = open_test_market(market, source)
    current = market.get_current_market(args=[]).call()
    assert current["market_id"] == identifier

    assert tx_execution_succeeded(market.claim_demo_credits(args=[]).transact())
    assert tx_execution_succeeded(
        market.place_position(args=[current["market_id"], "SILVER", 25]).transact()
    )

    gate_record = _gate.get_finality(args=[current["market_id"]]).call()
    assert gate_record["finalized"] is False

    claim_receipt = market.claim_position(args=[current["market_id"], "SILVER"]).transact()
    assert not tx_execution_succeeded(claim_receipt)


@pytest.mark.slow
@pytest.mark.live_demo
def test_expiry_finality_rotation_and_historical_claim():
    source = configured_source()
    gate, market = deploy_wired_pair(source)
    identifier = open_test_market(market, source)
    account = get_default_account()

    assert tx_execution_succeeded(market.claim_demo_credits(args=[]).transact())
    assert tx_execution_succeeded(market.place_position(args=[identifier, "GOLD", 25]).transact())
    assert tx_execution_succeeded(market.place_position(args=[identifier, "SILVER", 25]).transact())

    detail = market.get_market(args=[identifier]).call()
    end_at = datetime.fromisoformat(detail["end_at"].replace("Z", "+00:00"))
    while datetime.now(timezone.utc) < end_at + timedelta(seconds=5):
        time.sleep(min(30, max(1, int((end_at + timedelta(seconds=5) - datetime.now(timezone.utc)).total_seconds()))))

    settlement_receipt = market.request_settlement(args=[identifier]).transact()
    assert tx_execution_succeeded(settlement_receipt)

    finality = gate.get_finality(args=[identifier]).call()
    if not finality.get("finalized"):
        retry_receipt = market.retry_finality(args=[identifier]).transact()
        assert tx_execution_succeeded(retry_receipt)
        for _ in range(12):
            finality = gate.get_finality(args=[identifier]).call()
            if finality.get("finalized"):
                break
            time.sleep(10)
    assert finality["finalized"] is True

    outcome = market.get_market(args=[identifier]).call()["outcome"]
    winning_side = outcome if outcome in ("GOLD", "SILVER") else "GOLD"

    rotated_identifier = open_test_market(market, source)
    assert rotated_identifier != identifier

    claim_receipt = market.claim_position(args=[identifier, winning_side]).transact()
    assert tx_execution_succeeded(claim_receipt)
    historical_position = market.get_position(args=[identifier, account.address, winning_side]).call()
    assert historical_position["claimed"] is True
    assert historical_position["payout"] > 0

    duplicate_claim = market.claim_position(args=[identifier, winning_side]).transact()
    assert not tx_execution_succeeded(duplicate_claim)

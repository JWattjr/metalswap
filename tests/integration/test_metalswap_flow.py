"""Two-contract GenLayer integration coverage.

Run with a live GLSim/Studio network and the exact XAUS evidence origin:

    $env:METALSWAP_INTEGRATION_SOURCE_BASE_URL = "https://xaus.com/api/v1/intraday"
    gltest tests/integration/test_metalswap_flow.py -v -s

The tests intentionally deploy fresh contracts so they cannot mutate the
production deployment. A complete finalized settlement test should be run
against XAUS only after both instrument requests pass preflight. An HTTPS
fixture directory remains useful for synthetic lifecycle testing, but it does
not prove independent real-price retrieval.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from gltest import get_contract_factory
from gltest.accounts import get_default_account
from gltest.assertions import tx_execution_succeeded


XAUS_SOURCE_BASE_URL = "https://xaus.com/api/v1/intraday"
XAUS_EVIDENCE_URL = "https://xaus.com/api/v1/intraday?hours=48"


def configured_source() -> str:
    source = os.getenv("METALSWAP_INTEGRATION_SOURCE_BASE_URL", "").strip()
    if not source:
        pytest.skip("Set METALSWAP_INTEGRATION_SOURCE_BASE_URL to run live integration coverage.")
    if source == XAUS_SOURCE_BASE_URL:
        return source
    if not source.startswith("https://") or not source.endswith("/"):
        pytest.fail(
            "METALSWAP_INTEGRATION_SOURCE_BASE_URL must be the exact XAUS endpoint "
            "or an HTTPS directory with a trailing slash."
        )
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
    evidence_url = XAUS_EVIDENCE_URL if source == XAUS_SOURCE_BASE_URL else f"{source}{identifier}.json"
    receipt = market.open_market(
        args=[identifier, start_at, evidence_url]
    ).transact()
    assert tx_execution_succeeded(receipt)
    return identifier


def distinct_non_owner_accounts(accounts, owner_address: str, count: int = 2):
    distinct = []
    seen = {owner_address.lower()}
    for account in accounts:
        address = account.address.lower()
        if address not in seen:
            distinct.append(account)
            seen.add(address)
        if len(distinct) == count:
            return distinct
    pytest.skip(f"Live lifecycle requires {count} configured non-owner test accounts.")


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
    if source == XAUS_SOURCE_BASE_URL:
        assert config["source_mode"] == "XAUS_INDICATIVE_HISTORICAL_REPLAY"
        assert config["gold_instrument"] == "XAUUSD"
        assert config["silver_instrument"] == "XAGUSD"
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
def test_expiry_finality_rotation_and_historical_claim(accounts):
    source = configured_source()
    gate, market = deploy_wired_pair(source)
    identifier = open_test_market(market, source)
    owner = get_default_account()
    gold_account, silver_account = distinct_non_owner_accounts(accounts, owner.address)
    gold_market = market.connect(gold_account)
    silver_market = market.connect(silver_account)

    assert tx_execution_succeeded(gold_market.claim_demo_credits(args=[]).transact())
    assert tx_execution_succeeded(silver_market.claim_demo_credits(args=[]).transact())
    assert tx_execution_succeeded(gold_market.place_position(args=[identifier, "GOLD", 25]).transact())
    assert tx_execution_succeeded(silver_market.place_position(args=[identifier, "SILVER", 25]).transact())

    detail = market.get_market(args=[identifier]).call()
    end_at = datetime.fromisoformat(detail["end_at"].replace("Z", "+00:00"))
    while datetime.now(timezone.utc) < end_at + timedelta(seconds=5):
        time.sleep(min(30, max(1, int((end_at + timedelta(seconds=5) - datetime.now(timezone.utc)).total_seconds()))))

    settlement_receipt = gold_market.request_settlement(args=[identifier]).transact()
    assert tx_execution_succeeded(settlement_receipt)

    settled = market.get_market(args=[identifier]).call()
    assert settled["outcome"] in ("GOLD", "SILVER", "REFUND")
    assert settled["evidence_hash"].startswith("sha256:")
    attempts = settled["settlement_attempts"]
    repeat_receipt = silver_market.request_settlement(args=[identifier]).transact()
    assert tx_execution_succeeded(repeat_receipt)
    assert market.get_market(args=[identifier]).call()["settlement_attempts"] == attempts

    finality = gate.get_finality(args=[identifier]).call()
    if not finality.get("finalized"):
        retry_receipt = gold_market.retry_finality(args=[identifier]).transact()
        assert tx_execution_succeeded(retry_receipt)
        for _ in range(12):
            finality = gate.get_finality(args=[identifier]).call()
            if finality.get("finalized"):
                break
            time.sleep(10)
    assert finality["finalized"] is True
    assert market.get_market(args=[identifier]).call()["finality_status"] == "FINALIZED"

    outcome = market.get_market(args=[identifier]).call()["outcome"]
    winning_side = outcome if outcome in ("GOLD", "SILVER") else "GOLD"
    winning_account = gold_account if winning_side == "GOLD" else silver_account
    winning_market = market.connect(winning_account)

    rotated_identifier = open_test_market(market, source)
    assert rotated_identifier != identifier

    claim_receipt = winning_market.claim_position(args=[identifier, winning_side]).transact()
    assert tx_execution_succeeded(claim_receipt)
    historical_position = market.get_position(
        args=[identifier, winning_account.address, winning_side]
    ).call()
    assert historical_position["claimed"] is True
    assert historical_position["payout"] > 0

    duplicate_claim = winning_market.claim_position(args=[identifier, winning_side]).transact()
    assert not tx_execution_succeeded(duplicate_claim)

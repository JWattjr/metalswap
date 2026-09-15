import json

from tests.direct.conftest import as_address, evidence_payload, fund_and_stake, market_id, open_market, settle_with


def test_gold_outperforms_while_both_rise_and_payout_conserves_pool(
    market_contract, direct_vm, direct_alice, direct_bob
):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 300)
    fund_and_stake(market, direct_vm, direct_bob, identifier, "SILVER", 100)
    payload = evidence_payload(
        identifier,
        gold_opening_price=2_000_000_000,
        gold_closing_price=2_020_000_000,
        silver_opening_price=25_000_000,
        silver_closing_price=25_100_000,
    )
    settle_with(market, direct_vm, direct_alice, identifier, payload)

    detail = market.get_market(identifier)
    assert detail["outcome"] == "GOLD"
    assert detail["fee_amount"] == 8
    assert detail["distributable_pool"] == 392
    assert detail["status"] == "AWAITING_FINALITY"
    assert market.get_claim_quote(identifier, as_address(direct_alice), "GOLD")["payout"] == 392
    assert market.get_claim_quote(identifier, as_address(direct_bob), "SILVER")["payout"] == 0

    # A repeated settlement request is a no-op after the outcome is set.
    market.request_settlement(identifier)
    assert market.get_market(identifier)["settlement_attempts"] == 1


def test_silver_outperforms_while_both_rise(market_contract, direct_vm, direct_alice, direct_bob):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 100)
    fund_and_stake(market, direct_vm, direct_bob, identifier, "SILVER", 300)
    payload = evidence_payload(
        identifier,
        gold_opening_price=2_000_000_000,
        gold_closing_price=2_004_000_000,
        silver_opening_price=25_000_000,
        silver_closing_price=25_125_000,
    )
    settle_with(market, direct_vm, direct_alice, identifier, payload)
    assert market.get_market(identifier)["outcome"] == "SILVER"

    assert market.get_claim_quote(identifier, as_address(direct_bob), "SILVER")["payout"] == 392


def test_gold_outperforms_when_both_fall(market_contract, direct_vm, direct_alice, direct_bob):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 200)
    fund_and_stake(market, direct_vm, direct_bob, identifier, "SILVER", 200)
    payload = evidence_payload(
        identifier,
        gold_opening_price=2_000_000_000,
        gold_closing_price=1_998_000_000,
        silver_opening_price=25_000_000,
        silver_closing_price=24_750_000,
    )
    settle_with(market, direct_vm, direct_alice, identifier, payload)
    assert market.get_market(identifier)["outcome"] == "GOLD"


def test_equal_relative_returns_refund_without_fee(market_contract, direct_vm, direct_alice, direct_bob):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 200)
    fund_and_stake(market, direct_vm, direct_bob, identifier, "SILVER", 100)
    payload = evidence_payload(
        identifier,
        gold_opening_price=2_000_000_000,
        gold_closing_price=1_990_000_000,
        silver_opening_price=25_000_000,
        silver_closing_price=24_875_000,
    )
    settle_with(market, direct_vm, direct_alice, identifier, payload)
    detail = market.get_market(identifier)
    assert detail["outcome"] == "REFUND"
    assert detail["fee_amount"] == 0
    assert detail["distributable_pool"] == 300

    assert market.get_claim_quote(identifier, as_address(direct_alice), "GOLD")["payout"] == 200


def test_one_sided_pool_refunds_even_when_relative_returns_differ(market_contract, direct_vm, direct_alice):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 250)
    settle_with(market, direct_vm, direct_alice, identifier, evidence_payload(identifier))
    detail = market.get_market(identifier)
    assert detail["outcome"] == "REFUND"
    assert detail["fee_amount"] == 0
    assert market.get_claim_quote(identifier, as_address(direct_alice), "GOLD")["payout"] == 250


def test_cutoff_rejects_late_entry(market_contract, direct_vm, direct_alice):
    identifier = open_market(market_contract, direct_vm)
    direct_vm.sender = direct_alice
    market_contract.claim_demo_credits()
    direct_vm.warp("2025-01-01T00:15:00Z")
    with direct_vm.expect_revert("market entry is closed"):
        market_contract.place_position(identifier, "GOLD", 10)


def test_invalid_zero_prices_and_mismatched_timestamps_become_pending(
    market_contract, direct_vm, direct_alice
):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 100)
    payload = evidence_payload(
        identifier,
        opening="2025-01-01T00:14:00Z",
        gold_opening_price=0,
    )
    direct_vm.mock_web(
        rf".*{identifier}\.json$",
        {"status": 200, "body": json.dumps(payload)},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(identifier)
    detail = market.get_market(identifier)
    assert detail["outcome"] == ""
    assert detail["settlement_state"] == "PENDING_EVIDENCE"
    assert detail["last_reason_code"] == "INVALID_SCHEMA"


def test_missing_and_extra_fields_become_pending(market_contract, direct_vm, direct_alice):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "SILVER", 100)
    payload = evidence_payload(identifier)
    payload.pop("evidence_hash")
    payload["unexpected"] = "reject-me"
    direct_vm.mock_web(
        rf".*{identifier}\.json$",
        {"status": 200, "body": json.dumps(payload)},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(identifier)
    detail = market.get_market(identifier)
    assert detail["settlement_state"] == "PENDING_EVIDENCE"
    assert detail["outcome"] == ""


def test_missing_evidence_can_refund_after_frozen_deadline(market_contract, direct_vm, direct_alice):
    market = market_contract
    identifier = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, identifier, "GOLD", 100)
    direct_vm.mock_web(rf".*{identifier}\.json$", {"status": 404, "body": "not found"})
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(identifier)
    direct_vm.warp("2025-01-01T00:41:00Z")
    market.refund_after_deadline(identifier)
    assert market.get_market(identifier)["outcome"] == "REFUND"


def test_request_and_refund_after_deadline_share_fee_free_transition(
    market_contract, direct_vm, direct_owner, direct_alice, direct_bob
):
    market = market_contract
    first = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, first, "GOLD", 100)
    fund_and_stake(market, direct_vm, direct_bob, first, "SILVER", 100)
    direct_vm.mock_web(
        rf".*{first}\.json$",
        {"status": 200, "body": json.dumps(evidence_payload(first))},
    )
    direct_vm.warp("2025-01-01T00:40:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(first)
    first_detail = market.get_market(first)

    direct_vm.warp("2025-01-01T00:45:00Z")
    direct_vm.sender = direct_owner
    second = market_id("2025-01-01T01:00:00Z")
    market.open_market(
        second,
        "2025-01-01T01:00:00Z",
        f"https://metal-swap.vercel.app/evidence/{second}.json",
    )
    direct_vm.warp("2025-01-01T01:26:00Z")
    market.refund_after_deadline(second)
    second_detail = market.get_market(second)

    for detail in (first_detail, second_detail):
        assert detail["outcome"] == "REFUND"
        assert detail["settlement_state"] == "REFUND_PROVISIONAL"
        assert detail["last_reason_code"] == "SETTLEMENT_DEADLINE_REFUND"
        assert detail["fee_amount"] == 0
        assert detail["distributable_pool"] == detail["total_staked"]
    assert first_detail["settlement_attempts"] == 0
    assert second_detail["settlement_attempts"] == 0


def test_failed_transport_and_truncated_content_remain_pending(
    market_contract, direct_vm, direct_owner, direct_alice
):
    market = market_contract
    first = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, first, "GOLD", 100)
    direct_vm.mock_web(
        rf".*{first}\.json$",
        {"status": 503, "body": json.dumps(evidence_payload(first))},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(first)
    failed_transport = market.get_market(first)
    assert failed_transport["settlement_state"] == "PENDING_EVIDENCE"
    assert failed_transport["last_reason_code"] == "SOURCE_UNAVAILABLE"

    direct_vm.warp("2025-01-01T00:45:00Z")
    direct_vm.sender = direct_owner
    second = market_id("2025-01-01T01:00:00Z")
    market.open_market(
        second,
        "2025-01-01T01:00:00Z",
        f"https://metal-swap.vercel.app/evidence/{second}.json",
    )
    direct_vm.mock_web(
        rf".*{second}\.json$",
        {"status": 200, "body": b'{"schema_version":"metalswap-evidence-v1"'},
    )
    direct_vm.warp("2025-01-01T01:15:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(second)
    truncated = market.get_market(second)
    assert truncated["settlement_state"] == "PENDING_EVIDENCE"
    assert truncated["last_reason_code"] == "MALFORMED_JSON"


def test_excessive_evidence_body_and_numeric_value_are_rejected(
    market_contract, direct_vm, direct_owner, direct_alice
):
    market = market_contract
    first = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, first, "GOLD", 100)
    direct_vm.mock_web(
        rf".*{first}\.json$",
        {"status": 200, "body": "x" * (64 * 1_024 + 1)},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(first)
    assert market.get_market(first)["last_reason_code"] == "EVIDENCE_TOO_LARGE"

    direct_vm.warp("2025-01-01T00:45:00Z")
    direct_vm.sender = direct_owner
    second = market_id("2025-01-01T01:00:00Z")
    market.open_market(
        second,
        "2025-01-01T01:00:00Z",
        f"https://metal-swap.vercel.app/evidence/{second}.json",
    )
    payload = evidence_payload(second, gold_opening_price=1_000_000_000_001)
    direct_vm.mock_web(
        rf".*{second}\.json$",
        {"status": 200, "body": json.dumps(payload)},
    )
    direct_vm.warp("2025-01-01T01:15:00Z")
    direct_vm.sender = direct_alice
    market.request_settlement(second)
    assert market.get_market(second)["last_reason_code"] == "INVALID_SCHEMA"


def test_position_page_boundary_keeps_both_sides_of_one_market(
    market_contract, direct_vm, direct_alice
):
    identifier = open_market(market_contract, direct_vm)
    direct_vm.sender = direct_alice
    market_contract.claim_demo_credits()
    market_contract.place_position(identifier, "GOLD", 100)
    market_contract.place_position(identifier, "SILVER", 50)

    first = market_contract.get_user_positions(as_address(direct_alice), 0, 1)
    second = market_contract.get_user_positions(
        as_address(direct_alice), first["next_offset"], 1
    )

    assert [position["side"] for position in first["positions"]] == ["GOLD"]
    assert [position["side"] for position in second["positions"]] == ["SILVER"]
    assert second["total_positions"] == 2
    assert second["has_more"] is False


def test_historical_position_remains_inspectable_after_market_rotation(
    market_contract, direct_vm, direct_owner, direct_alice
):
    market = market_contract
    first = open_market(market, direct_vm)
    fund_and_stake(market, direct_vm, direct_alice, first, "GOLD", 100)
    fund_and_stake(market, direct_vm, direct_owner, first, "SILVER", 100)
    settle_with(market, direct_vm, direct_alice, first, evidence_payload(first))

    direct_vm.sender = direct_alice

    direct_vm.warp("2025-01-01T00:45:00Z")
    direct_vm.sender = direct_owner
    second = market_id("2025-01-01T01:00:00Z")
    market.open_market(
        second,
        "2025-01-01T01:00:00Z",
        f"https://metal-swap.vercel.app/evidence/{second}.json",
    )

    historical = market.get_position(first, as_address(direct_alice), "GOLD")
    page = market.get_user_positions(as_address(direct_alice), 0, 50)
    assert historical["exists"] is True
    assert historical["claimed"] is False
    assert market.get_claim_quote(first, as_address(direct_alice), "GOLD")["finality_status"] == "PENDING"
    assert [position["market_id"] for position in page["positions"]] == [first]


def test_claim_requires_finality_before_any_claim(
    market_contract, direct_vm, direct_owner, direct_alice
):
    identifier = open_market(market_contract, direct_vm)
    direct_vm.sender = direct_alice
    market_contract.claim_demo_credits()
    market_contract.place_position(identifier, "GOLD", 100)
    payload = evidence_payload(identifier)
    direct_vm.mock_web(
        rf".*{identifier}\.json$",
        {"status": 200, "body": json.dumps(payload)},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    market_contract.request_settlement(identifier)
    with direct_vm.expect_revert("settlement is not protocol-finalized"):
        market_contract.claim_position(identifier, "GOLD")

    # A wired market's finality record is applied in settle_with; this test
    # keeps the explicit gating failure above separate from the success path.


def test_market_opening_is_owner_only_and_bounded(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob
):
    market = direct_deploy("contracts/metalswap.py")
    identifier = market_id("2025-01-01T00:15:00Z")
    direct_vm.warp("2025-01-01T00:00:00Z")

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("owner authorization required"):
        market.open_market(
            identifier,
            "2025-01-01T00:15:00Z",
            f"https://metal-swap.vercel.app/evidence/{identifier}.json",
        )

    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("market setup is incomplete"):
        market.open_market(
            identifier,
            "2025-01-01T00:15:00Z",
            f"https://metal-swap.vercel.app/evidence/{identifier}.json",
        )

    market.configure_finality_gate(as_address(direct_bob))
    market.configure_source_base_url("https://metal-swap.vercel.app/evidence/")
    far_identifier = market_id("2025-01-02T00:00:00Z")
    with direct_vm.expect_revert("market start is too far in the future"):
        market.open_market(
            far_identifier,
            "2025-01-02T00:00:00Z",
            f"https://metal-swap.vercel.app/evidence/{far_identifier}.json",
        )

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("owner authorization required"):
        market.open_next_market()

    direct_vm.sender = direct_owner
    assert market.open_next_market() == market_id("2025-01-01T00:15:00Z")

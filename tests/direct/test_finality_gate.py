from tests.direct.conftest import as_address


def test_gate_records_finality_once_and_idempotently(gate_contract, direct_vm, direct_owner, direct_alice):
    gate = gate_contract
    market_address = as_address(direct_alice)
    direct_vm.sender = direct_owner
    gate.configure_market(market_address)
    direct_vm.sender = market_address
    args = (
        "market-2025-01-01T00:15:00Z",
        "GOLD",
        392,
        8,
        2_000_000_000,
        2_020_000_000,
        25_000_000,
        25_100_000,
        "https://metal-swap.vercel.app/evidence/market-2025-01-01T00:15:00Z.json",
        "sha256:" + "a" * 64,
    )
    gate.record_finality(*args)
    gate.record_finality(*args)
    assert gate.get_finality(args[0])["finalized"] is True
    assert gate.get_gate_status()["finalized_markets"] == 1


def test_gate_rejects_conflicting_finality_replay(gate_contract, direct_vm, direct_owner, direct_alice):
    gate = gate_contract
    market_address = as_address(direct_alice)
    direct_vm.sender = direct_owner
    gate.configure_market(market_address)
    direct_vm.sender = market_address
    args = (
        "market-2025-01-01T00:15:00Z",
        "REFUND",
        100,
        0,
        2_000_000_000,
        2_000_000_000,
        25_000_000,
        25_000_000,
        "https://metal-swap.vercel.app/evidence/market-2025-01-01T00:15:00Z.json",
        "",
    )
    gate.record_finality(*args)
    with direct_vm.expect_revert("finality record conflicts"):
        gate.record_finality(
            args[0],
            "GOLD",
            args[2],
            args[3],
            args[4],
            args[5],
            args[6],
            args[7],
            args[8],
            args[9],
        )

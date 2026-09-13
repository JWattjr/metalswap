"""Direct-mode fixtures for the MetalSwap contract suite."""

import hashlib
import json
import os
import tempfile

import pytest

from gltest.direct import loader
from gltest.direct.vm import VMContext


def _windows_safe_message_injection(vm):
    """Keep GLSim's message timestamp compatible with the Windows runner."""
    try:
        from genlayer.py import calldata
        from genlayer.py.types import Address
    except ImportError:
        return

    sender_address = vm.sender
    if isinstance(sender_address, bytes):
        sender_address = Address(sender_address)
    contract_address = vm._contract_address
    if isinstance(contract_address, bytes):
        contract_address = Address(contract_address)
    origin_address = vm.origin
    if isinstance(origin_address, bytes):
        origin_address = Address(origin_address)
    message_datetime = vm._datetime
    if isinstance(message_datetime, str) and len(message_datetime) >= 20 and message_datetime[19] == ".":
        message_datetime = message_datetime[:19] + "Z"
    if not isinstance(message_datetime, str) or len(message_datetime) != 20:
        message_datetime = "2025-01-01T00:00:00Z"
    message_data = {
        "contract_address": contract_address,
        "sender_address": sender_address,
        "origin_address": origin_address,
        "stack": [],
        "value": vm._value,
        "datetime": message_datetime,
        "is_init": False,
        "chain_id": vm._chain_id,
        "entry_kind": 0,
        "entry_data": b"",
        "entry_stage_data": None,
    }
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, calldata.encode(message_data))
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        paths = getattr(vm, "_metalswap_temp_message_paths", [])
        paths.append(path)
        vm._metalswap_temp_message_paths = paths
    finally:
        os.close(fd)


_original_cleanup = VMContext._cleanup_after_deactivate
_original_refresh = VMContext._refresh_gl_message
loader._inject_message_to_fd0 = _windows_safe_message_injection


def _refresh_with_timestamp(vm):
    _original_refresh(vm)
    try:
        import genlayer.gl as gl

        message_datetime = vm._datetime
        if isinstance(message_datetime, str) and len(message_datetime) >= 20 and message_datetime[19] == ".":
            message_datetime = message_datetime[:19] + "Z"
        if not isinstance(message_datetime, str) or len(message_datetime) != 20:
            message_datetime = "2025-01-01T00:00:00Z"
        if hasattr(gl, "message_raw") and gl.message_raw is not None:
            gl.message_raw["datetime"] = message_datetime
    except ImportError:
        pass


VMContext._refresh_gl_message = _refresh_with_timestamp


def _cleanup_with_deferred_temp_files(vm):
    _original_cleanup(vm)
    for path in getattr(vm, "_metalswap_temp_message_paths", []):
        try:
            os.unlink(path)
        except (FileNotFoundError, PermissionError):
            pass
    vm._metalswap_temp_message_paths = []


VMContext._cleanup_after_deactivate = _cleanup_with_deferred_temp_files


def as_address(address):
    if hasattr(address, "as_hex"):
        return address
    from genlayer.py.types import Address

    return Address(address)


def reset_known_contract():
    try:
        from genlayer.gl import genvm_contracts

        genvm_contracts.__known_contract__ = None
    except ImportError:
        pass


def market_id(start="2025-01-01T00:15:00Z"):
    return f"market-{start}"


def evidence_payload(
    market,
    opening="2025-01-01T00:15:00Z",
    closing="2025-01-01T00:30:00Z",
    gold_opening_price=2_000_000_000,
    gold_closing_price=2_020_000_000,
    silver_opening_price=25_000_000,
    silver_closing_price=25_100_000,
):
    payload = {
        "schema_version": "metalswap-evidence-v1",
        "status": "FINALIZED",
        "market_id": market,
        "source_id": "metalswap-synthetic-evidence-v1",
        "evidence_url": f"https://metal-swap.vercel.app/evidence/{market}.json",
        "currency": "USD",
        "unit": "USD_PER_TROY_OUNCE",
        "selection_rule": "exact_boundary_observation",
        "max_gap_seconds": 0,
        "max_skew_seconds": 0,
        "gold_opening_timestamp": opening,
        "gold_opening_price": gold_opening_price,
        "gold_closing_timestamp": closing,
        "gold_closing_price": gold_closing_price,
        "silver_opening_timestamp": opening,
        "silver_opening_price": silver_opening_price,
        "silver_closing_timestamp": closing,
        "silver_closing_price": silver_closing_price,
        "evidence_hash": "",
        "reason_code": "NONE",
    }
    hash_payload = {key: value for key, value in payload.items() if key != "evidence_hash"}
    payload["evidence_hash"] = "sha256:" + hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


@pytest.fixture
def market_contract(direct_deploy):
    reset_known_contract()
    return direct_deploy("contracts/metalswap.py")


@pytest.fixture
def gate_contract(direct_deploy):
    reset_known_contract()
    return direct_deploy("contracts/settlement_gate.py")


def open_market(contract, direct_vm, start="2025-01-01T00:15:00Z"):
    direct_vm.warp("2025-01-01T00:00:00Z")
    identifier = market_id(start)
    contract.open_market(
        identifier,
        start,
        f"https://metal-swap.vercel.app/evidence/{identifier}.json",
    )
    return identifier


def fund_and_stake(contract, direct_vm, address, identifier, side, amount):
    direct_vm.sender = address
    if not contract.get_account(as_address(address))["demo_credits_claimed"]:
        contract.claim_demo_credits()
    contract.place_position(identifier, side, amount)


def settle_with(contract, direct_vm, sender, identifier, payload):
    direct_vm.mock_web(
        rf".*{identifier}\.json$",
        {"status": 200, "body": json.dumps(payload)},
    )
    direct_vm.warp("2025-01-01T00:30:00Z")
    direct_vm.sender = sender
    contract.request_settlement(identifier)

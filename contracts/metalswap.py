# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""MetalSwap: one pair, one 15-minute relative-performance market.

The browser can show a provisional chart and a variable payout preview, but it
cannot choose the winner. After expiry, GenLayer validators independently read
the frozen evidence URL, agree on the exact four observations, and deterministic
code compares the two percentage returns with cross multiplication.

This build uses explicit demo credits. The contract does not represent
commodity ownership or real-money settlement.
"""

import hashlib
import json
from dataclasses import dataclass

from genlayer import *


ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_CONSENSUS = "[CONSENSUS]"

SIDE_GOLD = "GOLD"
SIDE_SILVER = "SILVER"
SIDES = (SIDE_GOLD, SIDE_SILVER)

OUTCOME_GOLD = "GOLD"
OUTCOME_SILVER = "SILVER"
OUTCOME_REFUND = "REFUND"
OUTCOMES = (OUTCOME_GOLD, OUTCOME_SILVER, OUTCOME_REFUND)

MARKET_UPCOMING = "UPCOMING"
MARKET_LIVE = "LIVE"
MARKET_AWAITING_SETTLEMENT = "AWAITING_SETTLEMENT"
MARKET_PENDING_EVIDENCE = "PENDING_EVIDENCE"
MARKET_AWAITING_FINALITY = "AWAITING_FINALITY"
MARKET_CLAIMABLE = "CLAIMABLE"
MARKET_REFUND = "REFUND"

SETTLEMENT_AWAITING = "AWAITING_SETTLEMENT"
SETTLEMENT_PENDING_EVIDENCE = "PENDING_EVIDENCE"
SETTLEMENT_PROVISIONAL = "SETTLED_PROVISIONAL"
SETTLEMENT_REFUND_PROVISIONAL = "REFUND_PROVISIONAL"

EVIDENCE_SCHEMA_VERSION = "metalswap-evidence-v1"
RULE_VERSION = "relative-return-cross-multiplication-v1"
SOURCE_ID = "metalswap-synthetic-evidence-v1"
XAUS_SOURCE_ID = "xaus-intraday-indicative-v1"
DEFAULT_SOURCE_BASE_URL = "https://metal-swap.vercel.app/evidence/"
XAUS_SOURCE_BASE_URL = "https://xaus.com/api/v1/intraday"
XAUS_EVIDENCE_URL = "https://xaus.com/api/v1/intraday?hours=48"
GOLD_INSTRUMENT = "SYNTHETIC-XAUUSD-SPOT"
SILVER_INSTRUMENT = "SYNTHETIC-XAGUSD-SPOT"
XAUS_GOLD_INSTRUMENT = "XAUUSD"
XAUS_SILVER_INSTRUMENT = "XAGUSD"
CURRENCY = "USD"
UNIT = "USD_PER_TROY_OUNCE"
SELECTION_RULE = "exact_boundary_observation"
XAUS_SELECTION_RULE = "latest_observation_at_or_before_boundary"

MARKET_SECONDS = 900
SETTLEMENT_GRACE_SECONDS = 600
MAX_MARKET_HORIZON_SECONDS = MARKET_SECONDS * 2
MAX_SETTLEMENT_ATTEMPTS = 3
MAX_GAP_SECONDS = 180
MAX_SKEW_SECONDS = 60
MAX_PRICE = 10**12
# XAUS publishes a 48-hour window at two-minute intervals (up to 1,500
# points). Keep the body bounded while leaving conservative room for the
# complete window, metadata, and normal JSON whitespace.
MAX_EVIDENCE_BODY_BYTES = 96 * 1_024
MAX_EVIDENCE_STRING_LENGTH = 2_048
MAX_XAUS_POINTS = 1_500
XAUS_INTERVAL_SECONDS = 120
XAUS_HISTORY_HOURS = 48
FEE_BPS = 200
BPS_DENOMINATOR = 10_000
PRICE_SCALE = 1_000_000
DEMO_CREDITS = 1_000

PENDING_REASONS = (
    "EVIDENCE_NOT_AVAILABLE",
    "SOURCE_UNAVAILABLE",
    "FIXTURE_NOT_FOUND",
    "MALFORMED_JSON",
    "EVIDENCE_TOO_LARGE",
    "INVALID_SCHEMA",
    "CONFLICTING_EVIDENCE",
)

EVIDENCE_FIELDS = (
    "schema_version",
    "status",
    "market_id",
    "source_id",
    "evidence_url",
    "currency",
    "unit",
    "selection_rule",
    "max_gap_seconds",
    "max_skew_seconds",
    "gold_opening_timestamp",
    "gold_opening_price",
    "gold_closing_timestamp",
    "gold_closing_price",
    "silver_opening_timestamp",
    "silver_opening_price",
    "silver_closing_timestamp",
    "silver_closing_price",
    "evidence_hash",
    "reason_code",
)


def _is_timestamp_value(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 20:
        return False
    if value[4] != "-" or value[7] != "-" or value[10] != "T":
        return False
    if value[13] != ":" or value[16] != ":" or value[19] != "Z":
        return False
    for index in (0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18):
        if value[index] < "0" or value[index] > "9":
            return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    hour = int(value[11:13])
    minute = int(value[14:16])
    second = int(value[17:19])
    if year < 1970 or month < 1 or month > 12:
        return False
    if hour > 23 or minute > 59 or second > 59:
        return False
    month_days = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    return 1 <= day <= month_days[month - 1]


def _timestamp_to_epoch_value(value: str) -> int:
    if not _is_timestamp_value(value):
        return -1
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    seconds = int(value[11:13]) * 3_600 + int(value[14:16]) * 60 + int(value[17:19])
    days = 0
    current_year = 1970
    while current_year < year:
        days += 366 if current_year % 4 == 0 and (current_year % 100 != 0 or current_year % 400 == 0) else 365
        current_year += 1
    month_days = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    month_index = 1
    while month_index < month:
        days += month_days[month_index - 1]
        month_index += 1
    return days * 86_400 + (day - 1) * 86_400 + seconds


def _timestamp_from_epoch_value(epoch: int) -> str:
    remaining = epoch
    year = 1970
    while True:
        year_days = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        if remaining < year_days * 86_400:
            break
        remaining -= year_days * 86_400
        year += 1
    month_days = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    month = 1
    while remaining >= month_days[month - 1] * 86_400:
        remaining -= month_days[month - 1] * 86_400
        month += 1
    day = remaining // 86_400 + 1
    remaining %= 86_400
    hour = remaining // 3_600
    remaining %= 3_600
    minute = remaining // 60
    second = remaining % 60
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


def _fixed_price_from_source_value(value) -> int:
    if isinstance(value, bool) or value is None:
        return -1
    raw = str(value)
    if raw.startswith("+") or raw.startswith("-") or raw.count(".") > 1 or "e" in raw.lower():
        return -1
    if "." in raw:
        whole, fraction = raw.split(".")
    else:
        whole, fraction = raw, ""
    if not whole or not whole.isdigit() or (fraction and not fraction.isdigit()) or len(fraction) > 6:
        return -1
    fixed = int(whole) * PRICE_SCALE + int(fraction.ljust(6, "0") or "0")
    if fixed <= 0 or fixed > MAX_PRICE:
        return -1
    return fixed


def _evidence_hash_payload(evidence: dict) -> dict:
    return {
        "schema_version": evidence["schema_version"],
        "status": evidence["status"],
        "market_id": evidence["market_id"],
        "source_id": evidence["source_id"],
        "evidence_url": evidence["evidence_url"],
        "currency": evidence["currency"],
        "unit": evidence["unit"],
        "selection_rule": evidence["selection_rule"],
        "max_gap_seconds": evidence["max_gap_seconds"],
        "max_skew_seconds": evidence["max_skew_seconds"],
        "gold_opening_timestamp": evidence["gold_opening_timestamp"],
        "gold_opening_price": evidence["gold_opening_price"],
        "gold_closing_timestamp": evidence["gold_closing_timestamp"],
        "gold_closing_price": evidence["gold_closing_price"],
        "silver_opening_timestamp": evidence["silver_opening_timestamp"],
        "silver_opening_price": evidence["silver_opening_price"],
        "silver_closing_timestamp": evidence["silver_closing_timestamp"],
        "silver_closing_price": evidence["silver_closing_price"],
        "reason_code": evidence["reason_code"],
    }


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pending_evidence_for_context(context: dict, reason_code: str) -> dict:
    if reason_code not in PENDING_REASONS:
        reason_code = "INVALID_SCHEMA"
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": "PENDING_EVIDENCE",
        "market_id": context["market_id"],
        "source_id": context["source_id"],
        "evidence_url": context["evidence_url"],
        "currency": context.get("currency", CURRENCY),
        "unit": context.get("unit", UNIT),
        "selection_rule": context.get("selection_rule", SELECTION_RULE),
        "max_gap_seconds": 0,
        "max_skew_seconds": 0,
        "gold_opening_timestamp": "",
        "gold_opening_price": 0,
        "gold_closing_timestamp": "",
        "gold_closing_price": 0,
        "silver_opening_timestamp": "",
        "silver_opening_price": 0,
        "silver_closing_timestamp": "",
        "silver_closing_price": 0,
        "evidence_hash": "",
        "reason_code": reason_code,
    }


def _require_exact_evidence_fields(value) -> None:
    if not isinstance(value, dict):
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence result must be an object")
    keys = list(value.keys())
    if len(keys) != len(EVIDENCE_FIELDS):
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence result has missing or unexpected fields")
    for field in EVIDENCE_FIELDS:
        if field not in value:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence result has missing or unexpected fields")


def _validate_evidence_payload(raw, context: dict) -> dict:
    _require_exact_evidence_fields(raw)
    string_fields = (
        "schema_version",
        "status",
        "market_id",
        "source_id",
        "evidence_url",
        "currency",
        "unit",
        "selection_rule",
        "gold_opening_timestamp",
        "gold_closing_timestamp",
        "silver_opening_timestamp",
        "silver_closing_timestamp",
        "evidence_hash",
        "reason_code",
    )
    for field in string_fields:
        if not isinstance(raw[field], str) or len(raw[field]) > MAX_EVIDENCE_STRING_LENGTH:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence field has invalid type or length")
    numeric_fields = (
        "max_gap_seconds",
        "max_skew_seconds",
        "gold_opening_price",
        "gold_closing_price",
        "silver_opening_price",
        "silver_closing_price",
    )
    for field in numeric_fields:
        if isinstance(raw[field], bool) or not isinstance(raw[field], int):
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence numeric field has invalid type")
    if raw["schema_version"] != EVIDENCE_SCHEMA_VERSION:
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} unsupported evidence schema")
    if raw["market_id"] != context["market_id"] or raw["source_id"] != context["source_id"]:
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence market identity mismatch")
    if raw["evidence_url"] != context["evidence_url"]:
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence URL is not frozen")
    if raw["currency"] != context.get("currency", CURRENCY) or raw["unit"] != context.get("unit", UNIT):
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} currency or unit mismatch")
    if raw["selection_rule"] != context.get("selection_rule", SELECTION_RULE):
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence selection rule mismatch")
    if raw["status"] == "PENDING_EVIDENCE":
        if raw["reason_code"] not in PENDING_REASONS:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} invalid pending reason")
        for field in (
            "gold_opening_timestamp",
            "gold_closing_timestamp",
            "silver_opening_timestamp",
            "silver_closing_timestamp",
            "evidence_hash",
        ):
            if raw[field] != "":
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} pending evidence contains data")
        for field in numeric_fields:
            if raw[field] != 0:
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} pending evidence contains data")
        return raw
    if raw["status"] != "FINALIZED" or raw["reason_code"] != "NONE":
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} unsupported evidence status")
    for field in (
        "gold_opening_timestamp",
        "gold_closing_timestamp",
        "silver_opening_timestamp",
        "silver_closing_timestamp",
    ):
        if not _is_timestamp_value(raw[field]):
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} {field} is not a valid UTC timestamp")
    if context["source_id"] == XAUS_SOURCE_ID:
        start_epoch = _timestamp_to_epoch_value(context["start_at"])
        end_epoch = _timestamp_to_epoch_value(context["end_at"])
        opening_times = (
            _timestamp_to_epoch_value(raw["gold_opening_timestamp"]),
            _timestamp_to_epoch_value(raw["silver_opening_timestamp"]),
        )
        closing_times = (
            _timestamp_to_epoch_value(raw["gold_closing_timestamp"]),
            _timestamp_to_epoch_value(raw["silver_closing_timestamp"]),
        )
        for timestamp in opening_times:
            if timestamp > start_epoch or start_epoch - timestamp > MAX_GAP_SECONDS:
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} opening observation is stale or after the boundary")
        for timestamp in closing_times:
            if timestamp > end_epoch or end_epoch - timestamp > MAX_GAP_SECONDS:
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} closing observation is stale or after the boundary")
        actual_gap = max(
            start_epoch - opening_times[0],
            start_epoch - opening_times[1],
            end_epoch - closing_times[0],
            end_epoch - closing_times[1],
        )
        actual_skew = max(
            abs(opening_times[0] - opening_times[1]),
            abs(closing_times[0] - closing_times[1]),
        )
        if actual_skew > MAX_SKEW_SECONDS:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} cross-metal timestamp skew exceeds frozen limit")
        if raw["max_gap_seconds"] != actual_gap or raw["max_skew_seconds"] != actual_skew:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence alignment summary is inconsistent")
    else:
        if raw["max_gap_seconds"] != 0 or raw["max_skew_seconds"] != 0:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} synthetic evidence alignment must be exact")
        if raw["gold_opening_timestamp"] != context["start_at"] or raw["silver_opening_timestamp"] != context["start_at"]:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} opening timestamps are inconsistent")
        if raw["gold_closing_timestamp"] != context["end_at"] or raw["silver_closing_timestamp"] != context["end_at"]:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} closing timestamps are inconsistent")
    for field in (
        "gold_opening_price",
        "gold_closing_price",
        "silver_opening_price",
        "silver_closing_price",
    ):
        if raw[field] <= 0 or raw[field] > MAX_PRICE:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} price is outside the frozen bounds")
    if not raw["evidence_hash"].startswith("sha256:") or len(raw["evidence_hash"]) != 71:
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} invalid evidence hash")
    for character in raw["evidence_hash"][7:]:
        if character not in "0123456789abcdef":
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} invalid evidence hash")
    expected_hash = _sha256_text(
        json.dumps(_evidence_hash_payload(raw), sort_keys=True, separators=(",", ":"))
    )
    if raw["evidence_hash"] != expected_hash:
        raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence hash mismatch")
    return raw


def _read_bounded_json_response(response):
    status = getattr(response, "status", None)
    if isinstance(status, bool) or not isinstance(status, int):
        return None, "SOURCE_UNAVAILABLE"
    if status == 404:
        return None, "FIXTURE_NOT_FOUND"
    if status < 200 or status >= 300:
        return None, "SOURCE_UNAVAILABLE"
    body = getattr(response, "body", None)
    try:
        if isinstance(body, bytes):
            if len(body) == 0:
                return None, "MALFORMED_JSON"
            if len(body) > MAX_EVIDENCE_BODY_BYTES:
                return None, "EVIDENCE_TOO_LARGE"
            text = body.decode("utf-8")
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
            if len(body_bytes) == 0:
                return None, "MALFORMED_JSON"
            if len(body_bytes) > MAX_EVIDENCE_BODY_BYTES:
                return None, "EVIDENCE_TOO_LARGE"
            text = body
        else:
            return None, "MALFORMED_JSON"
        return json.loads(text), ""
    except Exception:
        return None, "MALFORMED_JSON"


def _read_xaus_json(url: str):
    try:
        response = gl.nondet.web.get(url)
    except Exception:
        return None, "SOURCE_UNAVAILABLE"
    return _read_bounded_json_response(response)


def _parse_xaus_series(raw, symbol: str):
    if not isinstance(raw, dict):
        return None, "INVALID_SCHEMA"
    if raw.get("symbol") != symbol or raw.get("currency") != "USD" or raw.get("unit") != "troy_oz":
        return None, "INVALID_SCHEMA"
    if raw.get("hours") != XAUS_HISTORY_HOURS or raw.get("interval_seconds") != XAUS_INTERVAL_SECONDS:
        return None, "INVALID_SCHEMA"
    coverage_seconds = raw.get("coverage_seconds")
    if isinstance(coverage_seconds, bool) or not isinstance(coverage_seconds, int):
        return None, "INVALID_SCHEMA"
    if coverage_seconds <= 0 or coverage_seconds > XAUS_HISTORY_HOURS * 3_600:
        return None, "INVALID_SCHEMA"
    data_state = raw.get("data_state")
    if not isinstance(data_state, dict) or data_state.get("status") != "fresh" or data_state.get("source") != "sampler":
        return None, "SOURCE_UNAVAILABLE"
    points = raw.get("points")
    if not isinstance(points, list) or len(points) == 0 or len(points) > MAX_XAUS_POINTS:
        return None, "INVALID_SCHEMA"
    normalized = []
    previous_timestamp = -1
    for point in points:
        if not isinstance(point, dict):
            return None, "INVALID_SCHEMA"
        timestamp = point.get("t")
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp <= previous_timestamp:
            return None, "INVALID_SCHEMA"
        price = _fixed_price_from_source_value(point.get("p"))
        if price <= 0:
            return None, "INVALID_SCHEMA"
        normalized.append({"t": timestamp, "p": price})
        previous_timestamp = timestamp
    return normalized, ""


def _select_xaus_boundary_point(points, boundary_epoch: int):
    selected = None
    for point in points:
        if point["t"] <= boundary_epoch:
            selected = point
        else:
            break
    if selected is None or boundary_epoch - selected["t"] > MAX_GAP_SECONDS:
        return None
    return selected


def _read_xaus_evidence_for_context(context: dict) -> dict:
    base_url = context["evidence_url"]
    gold_raw, reason = _read_xaus_json(f"{base_url}&symbol=xau")
    if reason:
        return _pending_evidence_for_context(context, reason)
    silver_raw, reason = _read_xaus_json(f"{base_url}&symbol=xag")
    if reason:
        return _pending_evidence_for_context(context, reason)
    gold_points, reason = _parse_xaus_series(gold_raw, "xau")
    if reason:
        return _pending_evidence_for_context(context, reason)
    silver_points, reason = _parse_xaus_series(silver_raw, "xag")
    if reason:
        return _pending_evidence_for_context(context, reason)
    start_epoch = _timestamp_to_epoch_value(context["start_at"])
    end_epoch = _timestamp_to_epoch_value(context["end_at"])
    gold_open = _select_xaus_boundary_point(gold_points, start_epoch)
    silver_open = _select_xaus_boundary_point(silver_points, start_epoch)
    gold_close = _select_xaus_boundary_point(gold_points, end_epoch)
    silver_close = _select_xaus_boundary_point(silver_points, end_epoch)
    if gold_open is None or silver_open is None or gold_close is None or silver_close is None:
        return _pending_evidence_for_context(context, "EVIDENCE_NOT_AVAILABLE")
    opening_skew = abs(gold_open["t"] - silver_open["t"])
    closing_skew = abs(gold_close["t"] - silver_close["t"])
    if max(opening_skew, closing_skew) > MAX_SKEW_SECONDS:
        return _pending_evidence_for_context(context, "CONFLICTING_EVIDENCE")
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": "FINALIZED",
        "market_id": context["market_id"],
        "source_id": context["source_id"],
        "evidence_url": context["evidence_url"],
        "currency": context["currency"],
        "unit": context["unit"],
        "selection_rule": context["selection_rule"],
        "max_gap_seconds": max(
            start_epoch - gold_open["t"],
            start_epoch - silver_open["t"],
            end_epoch - gold_close["t"],
            end_epoch - silver_close["t"],
        ),
        "max_skew_seconds": max(opening_skew, closing_skew),
        "gold_opening_timestamp": _timestamp_from_epoch_value(gold_open["t"]),
        "gold_opening_price": gold_open["p"],
        "gold_closing_timestamp": _timestamp_from_epoch_value(gold_close["t"]),
        "gold_closing_price": gold_close["p"],
        "silver_opening_timestamp": _timestamp_from_epoch_value(silver_open["t"]),
        "silver_opening_price": silver_open["p"],
        "silver_closing_timestamp": _timestamp_from_epoch_value(silver_close["t"]),
        "silver_closing_price": silver_close["p"],
        "evidence_hash": "",
        "reason_code": "NONE",
    }
    evidence["evidence_hash"] = _sha256_text(
        json.dumps(_evidence_hash_payload(evidence), sort_keys=True, separators=(",", ":"))
    )
    try:
        return _validate_evidence_payload(evidence, context)
    except Exception:
        return _pending_evidence_for_context(context, "INVALID_SCHEMA")


def _read_evidence_for_context(context: dict) -> dict:
    try:
        response = gl.nondet.web.get(context["evidence_url"])
    except Exception:
        return _pending_evidence_for_context(context, "SOURCE_UNAVAILABLE")
    status = getattr(response, "status", None)
    if isinstance(status, bool) or not isinstance(status, int):
        return _pending_evidence_for_context(context, "SOURCE_UNAVAILABLE")
    if status == 404:
        return _pending_evidence_for_context(context, "FIXTURE_NOT_FOUND")
    if status < 200 or status >= 300:
        return _pending_evidence_for_context(context, "SOURCE_UNAVAILABLE")
    try:
        body = getattr(response, "body", None)
        if isinstance(body, bytes):
            if len(body) == 0:
                return _pending_evidence_for_context(context, "MALFORMED_JSON")
            if len(body) > MAX_EVIDENCE_BODY_BYTES:
                return _pending_evidence_for_context(context, "EVIDENCE_TOO_LARGE")
            text = body.decode("utf-8")
        elif isinstance(body, str):
            if len(body.encode("utf-8")) == 0:
                return _pending_evidence_for_context(context, "MALFORMED_JSON")
            if len(body.encode("utf-8")) > MAX_EVIDENCE_BODY_BYTES:
                return _pending_evidence_for_context(context, "EVIDENCE_TOO_LARGE")
            text = body
        else:
            return _pending_evidence_for_context(context, "MALFORMED_JSON")
        parsed = json.loads(text)
    except Exception:
        return _pending_evidence_for_context(context, "MALFORMED_JSON")
    try:
        return _validate_evidence_payload(parsed, context)
    except Exception:
        return _pending_evidence_for_context(context, "INVALID_SCHEMA")


@allow_storage
@dataclass
class Market:
    market_id: str
    start_at: str
    end_at: str
    settlement_deadline: str
    evidence_url: str
    source_id: str
    rule_version: str
    fee_bps: u256
    gold_pool: u256
    silver_pool: u256
    total_staked: u256
    settlement_state: str
    settlement_attempts: u256
    last_reason_code: str
    gold_opening_timestamp: str
    gold_closing_timestamp: str
    silver_opening_timestamp: str
    silver_closing_timestamp: str
    gold_opening_price: u256
    gold_closing_price: u256
    silver_opening_price: u256
    silver_closing_price: u256
    evidence_hash: str
    outcome: str
    distributable_pool: u256
    fee_amount: u256
    claimed_amount: u256
    created_at: str


@allow_storage
@dataclass
class Position:
    market_id: str
    owner: Address
    side: str
    stake: u256
    claimed: bool
    payout: u256
    entered_at: str


@gl.contract_interface
class SettlementGateInterface:
    class View:
        def get_finality(self, market_id: str) -> dict: ...

    class Write:
        def record_finality(
            self,
            market_id: str,
            outcome: str,
            distributable_pool: u256,
            fee_amount: u256,
            gold_opening_price: u256,
            gold_closing_price: u256,
            silver_opening_price: u256,
            silver_closing_price: u256,
            source_url: str,
            evidence_hash: str,
        ) -> None: ...


class MetalSwap(gl.Contract):
    """A two-sided, fully funded GOLD-vs-SILVER prediction market."""

    owner: Address
    finality_gate: Address
    finality_gate_configured: bool
    source_base_url: str
    source_base_configured: bool
    current_market_id: str
    markets: TreeMap[str, Market]
    market_ids: DynArray[str]
    positions: TreeMap[str, Position]
    position_keys_by_owner: TreeMap[str, str]
    position_counts: TreeMap[Address, u256]
    total_staked_by_owner: TreeMap[Address, u256]
    claimed_payouts_by_owner: TreeMap[Address, u256]
    demo_balances: TreeMap[Address, u256]
    demo_credits_claimed: TreeMap[Address, bool]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.finality_gate = gl.message.sender_address
        self.finality_gate_configured = False
        self.source_base_url = DEFAULT_SOURCE_BASE_URL
        self.source_base_configured = False
        self.current_market_id = ""

    # ------------------------------------------------------------------
    # Deterministic validation and UTC helpers
    # ------------------------------------------------------------------

    def _normalize_address(self, value: Address) -> Address:
        if isinstance(value, str):
            return Address(value)
        return value

    def _require_owner(self) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} owner authorization required")

    def _validate_side(self, value: str) -> str:
        if not isinstance(value, str):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} side must be a string")
        side = value.upper()
        if side not in SIDES:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} side must be GOLD or SILVER")
        return side

    def _is_timestamp(self, value: str) -> bool:
        if not isinstance(value, str) or len(value) != 20:
            return False
        if value[4] != "-" or value[7] != "-" or value[10] != "T":
            return False
        if value[13] != ":" or value[16] != ":" or value[19] != "Z":
            return False
        for index in (0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18):
            if value[index] < "0" or value[index] > "9":
                return False
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        second = int(value[17:19])
        if year < 1970 or month < 1 or month > 12:
            return False
        if hour > 23 or minute > 59 or second > 59:
            return False
        month_days = (
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        )
        return 1 <= day <= month_days[month - 1]

    def _validate_timestamp(self, value: str, label: str) -> None:
        if not self._is_timestamp(value):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} {label} must be UTC ISO-8601 YYYY-MM-DDTHH:MM:SSZ"
            )

    def _canonical_transaction_timestamp(self, value: str) -> str:
        if not isinstance(value, str):
            return ""
        if value.endswith("Z"):
            body = value[:-1]
        elif value.endswith("+00:00"):
            body = value[:-6]
        else:
            return ""
        if len(body) > 19:
            fraction = body[19:]
            if len(fraction) < 2 or fraction[0] != ".":
                return ""
            for character in fraction[1:]:
                if character < "0" or character > "9":
                    return ""
            body = body[:19]
        candidate = body + "Z"
        return candidate if self._is_timestamp(candidate) else ""

    def _transaction_time(self) -> str:
        message = getattr(gl, "message", None)
        value = getattr(message, "datetime", None)
        if value is not None:
            normalized = self._canonical_transaction_timestamp(str(value))
            if normalized:
                return normalized
        raw = getattr(gl, "message_raw", None)
        if raw is not None:
            value = raw.get("datetime")
            if value is not None:
                normalized = self._canonical_transaction_timestamp(str(value))
                if normalized:
                    return normalized
        raise gl.vm.UserError(f"{ERROR_EXPECTED} transaction timestamp unavailable")

    def _timestamp_to_epoch(self, value: str) -> int:
        self._validate_timestamp(value, "timestamp")
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        seconds = int(value[11:13]) * 3_600 + int(value[14:16]) * 60 + int(value[17:19])
        days = 0
        current_year = 1970
        while current_year < year:
            days += 366 if current_year % 4 == 0 and (current_year % 100 != 0 or current_year % 400 == 0) else 365
            current_year += 1
        month_days = (
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        )
        month_index = 1
        while month_index < month:
            days += month_days[month_index - 1]
            month_index += 1
        return days * 86_400 + (day - 1) * 86_400 + seconds

    def _add_seconds(self, value: str, seconds: int) -> str:
        self._validate_timestamp(value, "timestamp")
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        remaining = int(value[11:13]) * 3_600 + int(value[14:16]) * 60 + int(value[17:19]) + seconds
        while remaining >= 86_400:
            remaining -= 86_400
            day += 1
            month_days = 29 if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else (28 if month == 2 else (30 if month in (4, 6, 9, 11) else 31))
            if day > month_days:
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        hour = remaining // 3_600
        remaining %= 3_600
        minute = remaining // 60
        second = remaining % 60
        return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"

    def _next_quarter_hour(self, value: str) -> str:
        minute = int(value[14:16])
        second = int(value[17:19])
        remainder = minute % 15
        delta = (15 - remainder) * 60 - second
        if delta <= 0:
            delta = MARKET_SECONDS
        return self._add_seconds(value, delta)

    def _market_id(self, start_at: str) -> str:
        return f"market-{start_at}"

    def _position_key(self, market_id: str, address: Address, side: str) -> str:
        return f"{market_id}|{address.as_hex.lower()}|{side}"

    def _owner_position_index_key(self, address: Address, index: u256) -> str:
        return f"{address.as_hex.lower()}|{index}"

    def _require_market(self, market_id: str) -> Market:
        if not isinstance(market_id, str) or len(market_id) == 0 or len(market_id) > 96:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market id")
        if market_id not in self.markets:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market does not exist")
        return self.markets[market_id]

    def _uses_xaus_source(self) -> bool:
        return self.source_base_url == XAUS_SOURCE_BASE_URL

    def _configured_source_id(self) -> str:
        return XAUS_SOURCE_ID if self._uses_xaus_source() else SOURCE_ID

    def _empty_market(self, market_id: str, start_at: str, evidence_url: str) -> Market:
        end_at = self._add_seconds(start_at, MARKET_SECONDS)
        return Market(
            market_id=market_id,
            start_at=start_at,
            end_at=end_at,
            settlement_deadline=self._add_seconds(end_at, SETTLEMENT_GRACE_SECONDS),
            evidence_url=evidence_url,
            source_id=self._configured_source_id(),
            rule_version=RULE_VERSION,
            fee_bps=FEE_BPS,
            gold_pool=0,
            silver_pool=0,
            total_staked=0,
            settlement_state=SETTLEMENT_AWAITING,
            settlement_attempts=0,
            last_reason_code="",
            gold_opening_timestamp="",
            gold_closing_timestamp="",
            silver_opening_timestamp="",
            silver_closing_timestamp="",
            gold_opening_price=0,
            gold_closing_price=0,
            silver_opening_price=0,
            silver_closing_price=0,
            evidence_hash="",
            outcome="",
            distributable_pool=0,
            fee_amount=0,
            claimed_amount=0,
            created_at=self._transaction_time(),
        )

    # ------------------------------------------------------------------
    # Canonical evidence and validator agreement
    # ------------------------------------------------------------------

    def _evidence_context(self, market: Market) -> dict:
        # Snapshot ordinary values before entering nondeterministic execution.
        # Consensus closures must not capture storage-backed objects or self.
        return {
            "market_id": market.market_id,
            "start_at": market.start_at,
            "end_at": market.end_at,
            "source_id": market.source_id,
            "evidence_url": market.evidence_url,
            "currency": CURRENCY,
            "unit": UNIT,
            "selection_rule": XAUS_SELECTION_RULE if market.source_id == XAUS_SOURCE_ID else SELECTION_RULE,
        }

    def _expected_evidence_url(self, market_id: str) -> str:
        if self._uses_xaus_source():
            return XAUS_EVIDENCE_URL
        return f"{self.source_base_url}{market_id}.json"

    def _validate_evidence_result(self, raw, market: Market) -> dict:
        return _validate_evidence_payload(raw, self._evidence_context(market))

    def _read_evidence(self, market: Market) -> dict:
        if market.source_id == XAUS_SOURCE_ID:
            return _read_xaus_evidence_for_context(self._evidence_context(market))
        return _read_evidence_for_context(self._evidence_context(market))

    def _consensus_evidence(self, market: Market) -> dict:
        context = self._evidence_context(market)

        def leader_fn() -> dict:
            if context["source_id"] == XAUS_SOURCE_ID:
                return _read_xaus_evidence_for_context(context)
            return _read_evidence_for_context(context)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader = _validate_evidence_payload(leader_result.calldata, context)
                validator = (
                    _read_xaus_evidence_for_context(context)
                    if context["source_id"] == XAUS_SOURCE_ID
                    else _read_evidence_for_context(context)
                )
                return leader == validator
            except Exception:
                return False

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    # ------------------------------------------------------------------
    # Configuration and market lifecycle
    # ------------------------------------------------------------------

    @gl.public.write
    def configure_finality_gate(self, gate_address: Address) -> None:
        self._require_owner()
        if self.finality_gate_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} finality gate already configured")
        gate_address = self._normalize_address(gate_address)
        if gate_address.as_hex == "0x0000000000000000000000000000000000000000" or gate_address == self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid finality gate address")
        self.finality_gate = gate_address
        self.finality_gate_configured = True

    @gl.public.write
    def configure_source_base_url(self, source_base_url: str) -> None:
        self._require_owner()
        if len(self.market_ids) != 0 or self.source_base_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source is already frozen")
        if not isinstance(source_base_url, str) or not source_base_url.startswith("https://") or len(source_base_url) > 200:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source base URL must be HTTPS")
        is_synthetic_directory = source_base_url.endswith("/")
        is_xaus_source = source_base_url == XAUS_SOURCE_BASE_URL
        if not is_synthetic_directory and not is_xaus_source:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source must be a frozen HTTPS directory or the approved XAUS endpoint")
        self.source_base_url = source_base_url
        self.source_base_configured = True

    def _open_market(self, market_id: str, start_at: str, evidence_url: str) -> None:
        self._validate_timestamp(start_at, "market start")
        if int(start_at[14:16]) % 15 != 0 or start_at[17:19] != "00":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market start must be a UTC quarter-hour")
        if market_id != self._market_id(start_at):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market id does not match its start")
        expected_url = self._expected_evidence_url(market_id)
        if evidence_url != expected_url:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} evidence URL must match the frozen source")
        now = self._transaction_time()
        now_year = int(now[0:4])
        start_year = int(start_at[0:4])
        if start_year > now_year + 1:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market start is too far in the future")
        now_epoch = self._timestamp_to_epoch(now)
        start_epoch = self._timestamp_to_epoch(start_at)
        if start_epoch <= now_epoch:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market start must be in the future")
        if start_epoch - now_epoch > MAX_MARKET_HORIZON_SECONDS:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market start is too far in the future")
        if not self.source_base_configured or not self.finality_gate_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market setup is incomplete")
        if market_id in self.markets:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market already exists")
        if self.current_market_id and self.current_market_id in self.markets:
            current = self.markets[self.current_market_id]
            current_start_epoch = self._timestamp_to_epoch(current.start_at)
            if now_epoch < self._timestamp_to_epoch(current.end_at):
                raise gl.vm.UserError(f"{ERROR_EXPECTED} an active market already exists")
            if start_epoch <= current_start_epoch:
                raise gl.vm.UserError(f"{ERROR_EXPECTED} market must move forward in time")
        self.markets[market_id] = self._empty_market(market_id, start_at, evidence_url)
        self.market_ids.append(market_id)
        self.current_market_id = market_id

    @gl.public.write
    def open_market(self, market_id: str, start_at: str, evidence_url: str) -> None:
        self._require_owner()
        self._open_market(market_id, start_at, evidence_url)

    @gl.public.write
    def open_next_market(self) -> str:
        self._require_owner()
        now = self._transaction_time()
        start_at = self._next_quarter_hour(now)
        market_id = self._market_id(start_at)
        self._open_market(market_id, start_at, self._expected_evidence_url(market_id))
        return market_id

    @gl.public.write
    def claim_demo_credits(self) -> None:
        sender = gl.message.sender_address
        if self.demo_credits_claimed.get(sender, False):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} demo credits already claimed")
        self.demo_credits_claimed[sender] = True
        self.demo_balances[sender] = self.demo_balances.get(sender, 0) + DEMO_CREDITS

    @gl.public.write
    def place_position(self, market_id: str, side: str, amount: u256) -> None:
        market = self._require_market(market_id)
        side = self._validate_side(side)
        if amount <= 0:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} stake must be positive")
        now = self._transaction_time()
        if self._timestamp_to_epoch(now) >= self._timestamp_to_epoch(market.start_at):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market entry is closed")
        sender = gl.message.sender_address
        balance = self.demo_balances.get(sender, 0)
        if balance < amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} insufficient demo credits")
        self.demo_balances[sender] = balance - amount
        if side == SIDE_GOLD:
            market.gold_pool += amount
        else:
            market.silver_pool += amount
        market.total_staked += amount
        key = self._position_key(market_id, sender, side)
        if key in self.positions:
            position = self.positions[key]
            if position.claimed:
                raise gl.vm.UserError(f"{ERROR_EXPECTED} claimed position cannot receive more stake")
            position.stake += amount
            self.positions[key] = position
        else:
            self.positions[key] = Position(
                market_id=market_id,
                owner=sender,
                side=side,
                stake=amount,
                claimed=False,
                payout=0,
                entered_at=now,
            )
            position_index = self.position_counts.get(sender, 0)
            self.position_keys_by_owner[self._owner_position_index_key(sender, position_index)] = key
            self.position_counts[sender] = position_index + 1
        self.total_staked_by_owner[sender] = self.total_staked_by_owner.get(sender, 0) + amount
        self.markets[market_id] = market

    # ------------------------------------------------------------------
    # Settlement and finality-gated claims
    # ------------------------------------------------------------------

    def _market_is_final(self, market_id: str) -> bool:
        if not self.finality_gate_configured:
            return False
        try:
            market = self._require_market(market_id)
            record = SettlementGateInterface(self.finality_gate).view().get_finality(market_id)
            if not isinstance(record, dict) or record.get("finalized") is not True:
                return False
            return (
                record.get("market_id") == market.market_id
                and record.get("outcome") == market.outcome
                and record.get("distributable_pool") == market.distributable_pool
                and record.get("fee_amount") == market.fee_amount
                and record.get("gold_opening_price") == market.gold_opening_price
                and record.get("gold_closing_price") == market.gold_closing_price
                and record.get("silver_opening_price") == market.silver_opening_price
                and record.get("silver_closing_price") == market.silver_closing_price
                and record.get("source_url") == market.evidence_url
                and record.get("evidence_hash") == market.evidence_hash
            )
        except Exception:
            return False

    def _emit_finality(self, market: Market) -> None:
        if not self.finality_gate_configured:
            return
        SettlementGateInterface(self.finality_gate).emit(on="finalized").record_finality(
            market.market_id,
            market.outcome,
            market.distributable_pool,
            market.fee_amount,
            market.gold_opening_price,
            market.gold_closing_price,
            market.silver_opening_price,
            market.silver_closing_price,
            market.evidence_url,
            market.evidence_hash,
        )

    def _apply_evidence(self, market: Market, evidence: dict) -> None:
        market.settlement_attempts += 1
        if evidence["status"] != "FINALIZED":
            market.settlement_state = SETTLEMENT_PENDING_EVIDENCE
            market.last_reason_code = evidence["reason_code"]
            self.markets[market.market_id] = market
            return

        market.gold_opening_timestamp = evidence["gold_opening_timestamp"]
        market.gold_closing_timestamp = evidence["gold_closing_timestamp"]
        market.silver_opening_timestamp = evidence["silver_opening_timestamp"]
        market.silver_closing_timestamp = evidence["silver_closing_timestamp"]
        market.gold_opening_price = evidence["gold_opening_price"]
        market.gold_closing_price = evidence["gold_closing_price"]
        market.silver_opening_price = evidence["silver_opening_price"]
        market.silver_closing_price = evidence["silver_closing_price"]
        market.evidence_hash = evidence["evidence_hash"]

        gold_cross = market.gold_closing_price * market.silver_opening_price
        silver_cross = market.silver_closing_price * market.gold_opening_price
        if market.gold_pool == 0 or market.silver_pool == 0 or gold_cross == silver_cross:
            market.outcome = OUTCOME_REFUND
            market.distributable_pool = market.total_staked
            market.fee_amount = 0
            market.settlement_state = SETTLEMENT_REFUND_PROVISIONAL
        else:
            gross_pool = market.gold_pool + market.silver_pool
            market.fee_amount = (gross_pool * market.fee_bps) // BPS_DENOMINATOR
            market.distributable_pool = gross_pool - market.fee_amount
            market.outcome = OUTCOME_GOLD if gold_cross > silver_cross else OUTCOME_SILVER
            market.settlement_state = SETTLEMENT_PROVISIONAL
        market.last_reason_code = ""
        self.markets[market.market_id] = market
        self._emit_finality(market)

    def _apply_deadline_refund(self, market: Market) -> None:
        if market.outcome:
            return
        market.outcome = OUTCOME_REFUND
        market.distributable_pool = market.total_staked
        market.fee_amount = 0
        market.last_reason_code = "SETTLEMENT_DEADLINE_REFUND"
        market.settlement_state = SETTLEMENT_REFUND_PROVISIONAL
        self.markets[market.market_id] = market
        self._emit_finality(market)

    @gl.public.write
    def request_settlement(self, market_id: str) -> None:
        market = self._require_market(market_id)
        now = self._transaction_time()
        now_epoch = self._timestamp_to_epoch(now)
        if market.outcome:
            return
        if now_epoch < self._timestamp_to_epoch(market.end_at):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market has not ended")
        # Once the frozen deadline is reached, settlement can never perform
        # another nondeterministic read. Both entry points share this exact
        # fee-free refund transition.
        if now_epoch >= self._timestamp_to_epoch(market.settlement_deadline):
            self._apply_deadline_refund(market)
            return
        if market.settlement_attempts >= MAX_SETTLEMENT_ATTEMPTS:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} settlement retry limit reached")
        evidence = self._consensus_evidence(market)
        self._apply_evidence(market, evidence)

    @gl.public.write
    def refund_after_deadline(self, market_id: str) -> None:
        market = self._require_market(market_id)
        now = self._transaction_time()
        if self._timestamp_to_epoch(now) < self._timestamp_to_epoch(market.settlement_deadline):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} settlement deadline has not passed")
        if market.outcome:
            return
        self._apply_deadline_refund(market)

    @gl.public.write
    def retry_finality(self, market_id: str) -> None:
        market = self._require_market(market_id)
        if not market.outcome:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market is not settled")
        if not self.finality_gate_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} finality gate is not configured")
        if self._market_is_final(market_id):
            return
        if market.settlement_state not in (SETTLEMENT_PROVISIONAL, SETTLEMENT_REFUND_PROVISIONAL):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} settlement is not ready for finality")
        # SettlementGate authenticates this callback as coming from this
        # contract and accepts only an exact, idempotent payload replay.
        self._emit_finality(market)

    def _require_finality(self, market_id: str) -> None:
        if not self.finality_gate_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} finality gate is not configured")
        if not self._market_is_final(market_id):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} settlement is not protocol-finalized")

    def _calculate_payout(self, market: Market, position: Position) -> u256:
        if not market.outcome:
            return 0
        if market.outcome == OUTCOME_REFUND:
            return position.stake
        if position.side != market.outcome:
            return 0
        winning_pool = market.gold_pool if market.outcome == OUTCOME_GOLD else market.silver_pool
        if winning_pool == 0:
            return 0
        return (market.distributable_pool * position.stake) // winning_pool

    @gl.public.write
    def claim_position(self, market_id: str, side: str) -> None:
        market = self._require_market(market_id)
        side = self._validate_side(side)
        self._require_finality(market_id)
        if not market.outcome:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market is not settled")
        key = self._position_key(market_id, gl.message.sender_address, side)
        if key not in self.positions:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} position does not exist")
        position = self.positions[key]
        if position.claimed:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} position already claimed")
        payout = self._calculate_payout(market, position)
        remaining = market.distributable_pool - market.claimed_amount
        if payout > remaining:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} payout exceeds distributable pool")
        position.claimed = True
        position.payout = payout
        market.claimed_amount += payout
        self.positions[key] = position
        self.markets[market_id] = market
        sender = gl.message.sender_address
        self.claimed_payouts_by_owner[sender] = self.claimed_payouts_by_owner.get(sender, 0) + payout
        if payout > 0:
            self.demo_balances[sender] = self.demo_balances.get(sender, 0) + payout

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def _display_status(self, market: Market) -> str:
        if market.outcome:
            if self._market_is_final(market.market_id):
                return MARKET_REFUND if market.outcome == OUTCOME_REFUND else MARKET_CLAIMABLE
            return MARKET_AWAITING_FINALITY
        now = self._timestamp_to_epoch(self._transaction_time())
        start = self._timestamp_to_epoch(market.start_at)
        end = self._timestamp_to_epoch(market.end_at)
        if now < start:
            return MARKET_UPCOMING
        if now < end:
            return MARKET_LIVE
        if market.settlement_state == SETTLEMENT_PENDING_EVIDENCE:
            return MARKET_PENDING_EVIDENCE
        return MARKET_AWAITING_SETTLEMENT

    def _market_to_dict(self, market: Market) -> dict:
        finalized = self._market_is_final(market.market_id)
        return {
            "exists": True,
            "market_id": market.market_id,
            "start_at": market.start_at,
            "end_at": market.end_at,
            "settlement_deadline": market.settlement_deadline,
            "evidence_url": market.evidence_url,
            "source_id": market.source_id,
            "rule_version": market.rule_version,
            "fee_bps": market.fee_bps,
            "fee_percent_display": "2%",
            "price_scale": PRICE_SCALE,
            "gold_pool": market.gold_pool,
            "silver_pool": market.silver_pool,
            "total_staked": market.total_staked,
            "settlement_state": market.settlement_state,
            "settlement_attempts": market.settlement_attempts,
            "last_reason_code": market.last_reason_code,
            "gold_opening_timestamp": market.gold_opening_timestamp,
            "gold_closing_timestamp": market.gold_closing_timestamp,
            "silver_opening_timestamp": market.silver_opening_timestamp,
            "silver_closing_timestamp": market.silver_closing_timestamp,
            "gold_opening_price": market.gold_opening_price,
            "gold_closing_price": market.gold_closing_price,
            "silver_opening_price": market.silver_opening_price,
            "silver_closing_price": market.silver_closing_price,
            "evidence_hash": market.evidence_hash,
            "outcome": market.outcome,
            "distributable_pool": market.distributable_pool,
            "fee_amount": market.fee_amount,
            "claimed_amount": market.claimed_amount,
            "finality_status": "FINALIZED" if finalized else ("PROVISIONAL" if market.outcome else "NOT_STARTED"),
            "status": self._display_status(market),
            "created_at": market.created_at,
        }

    def _position_to_dict(self, position: Position) -> dict:
        return {
            "exists": True,
            "market_id": position.market_id,
            "owner": position.owner.as_hex,
            "side": position.side,
            "stake": position.stake,
            "claimed": position.claimed,
            "payout": position.payout,
            "entered_at": position.entered_at,
        }

    @gl.public.view
    def get_protocol_config(self) -> dict:
        uses_xaus = self._uses_xaus_source()
        return {
            "owner": self.owner.as_hex,
            "fee_bps": FEE_BPS,
            "fee_percent_display": "2%",
            "market_seconds": MARKET_SECONDS,
            "max_market_horizon_seconds": MAX_MARKET_HORIZON_SECONDS,
            "settlement_grace_seconds": SETTLEMENT_GRACE_SECONDS,
            "max_settlement_attempts": MAX_SETTLEMENT_ATTEMPTS,
            "max_gap_seconds": MAX_GAP_SECONDS,
            "max_skew_seconds": MAX_SKEW_SECONDS,
            "price_scale": PRICE_SCALE,
            "rounding_policy": "floor each proportional payout; dust remains undistributed",
            "refund_policy": "equal relative returns, one-sided pools, or deadline expiry refund stakes without fees",
            "source_id": XAUS_SOURCE_ID if uses_xaus else SOURCE_ID,
            "source_base_url": self.source_base_url,
            "source_base_configured": self.source_base_configured,
            "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
            "rule_version": RULE_VERSION,
            "selection_rule": XAUS_SELECTION_RULE if uses_xaus else SELECTION_RULE,
            "gold_instrument": XAUS_GOLD_INSTRUMENT if uses_xaus else GOLD_INSTRUMENT,
            "silver_instrument": XAUS_SILVER_INSTRUMENT if uses_xaus else SILVER_INSTRUMENT,
            "currency": CURRENCY,
            "unit": UNIT,
            "source_mode": "XAUS_INDICATIVE_HISTORICAL_REPLAY" if uses_xaus else "SYNTHETIC_DEMO",
            "source_terms_url": "https://xaus.com/api/" if uses_xaus else "",
            "source_history_hours": XAUS_HISTORY_HOURS if uses_xaus else 0,
            "synthetic_demo": not uses_xaus,
            "finality_gate_configured": self.finality_gate_configured,
        }

    @gl.public.view
    def get_current_market(self) -> dict:
        if not self.current_market_id or self.current_market_id not in self.markets:
            return {"exists": False, "market_id": ""}
        return self._market_to_dict(self.markets[self.current_market_id])

    @gl.public.view
    def get_market(self, market_id: str) -> dict:
        return self._market_to_dict(self._require_market(market_id))

    @gl.public.view
    def get_market_ids(self, offset: u256, limit: u256) -> dict:
        if limit == 0 or limit > 50:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market page limit")
        end = offset + limit
        if end > len(self.market_ids):
            end = len(self.market_ids)
        result = []
        index = offset
        while index < end:
            result.append(self.market_ids[index])
            index += 1
        return {
            "market_ids": result,
            "total": len(self.market_ids),
            "offset": offset,
            "limit": limit,
            "next_offset": end,
            "has_more": end < len(self.market_ids),
        }

    @gl.public.view
    def get_position(self, market_id: str, owner: Address, side: str) -> dict:
        market = self._require_market(market_id)
        owner = self._normalize_address(owner)
        side = self._validate_side(side)
        key = self._position_key(market.market_id, owner, side)
        if key not in self.positions:
            return {"exists": False, "market_id": market.market_id, "owner": owner.as_hex, "side": side}
        return self._position_to_dict(self.positions[key])

    @gl.public.view
    def get_claim_quote(self, market_id: str, owner: Address, side: str) -> dict:
        market = self._require_market(market_id)
        owner = self._normalize_address(owner)
        side = self._validate_side(side)
        key = self._position_key(market.market_id, owner, side)
        if key not in self.positions:
            return {
                "exists": False,
                "market_id": market.market_id,
                "side": side,
                "payout": 0,
                "claimed": False,
                "finality_status": "FINALIZED" if self._market_is_final(market.market_id) else "PENDING",
            }
        position = self.positions[key]
        return {
            "exists": True,
            "market_id": market.market_id,
            "side": side,
            "stake": position.stake,
            "payout": self._calculate_payout(market, position),
            "claimed": position.claimed,
            "finality_status": "FINALIZED" if self._market_is_final(market.market_id) else "PENDING",
            "rounding_policy": "floor each proportional payout",
        }

    @gl.public.view
    def get_user_positions(self, owner: Address, offset: u256, limit: u256) -> dict:
        if limit == 0 or limit > 50:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid position page limit")
        owner = self._normalize_address(owner)
        result = []
        total_positions = self.position_counts.get(owner, 0)
        end = offset + limit
        if end > total_positions:
            end = total_positions
        index = offset
        while index < end:
            indexed_key = self.position_keys_by_owner.get(
                self._owner_position_index_key(owner, index),
                "",
            )
            if indexed_key and indexed_key in self.positions:
                result.append(self._position_to_dict(self.positions[indexed_key]))
            index += 1
        return {
            "positions": result,
            "total_markets": len(self.market_ids),
            "total_positions": total_positions,
            "offset": offset,
            "limit": limit,
            "next_offset": end,
            "has_more": end < total_positions,
        }

    @gl.public.view
    def get_account(self, owner: Address) -> dict:
        owner = self._normalize_address(owner)
        return {
            "owner": owner.as_hex,
            "demo_balance": self.demo_balances.get(owner, 0),
            "demo_credits_claimed": self.demo_credits_claimed.get(owner, False),
            "position_count": self.position_counts.get(owner, 0),
            "total_staked": self.total_staked_by_owner.get(owner, 0),
            "claimed_payouts": self.claimed_payouts_by_owner.get(owner, 0),
        }

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
DEFAULT_SOURCE_BASE_URL = "https://metal-swap.vercel.app/evidence/"
GOLD_INSTRUMENT = "SYNTHETIC-XAUUSD-SPOT"
SILVER_INSTRUMENT = "SYNTHETIC-XAGUSD-SPOT"
CURRENCY = "USD"
UNIT = "USD_PER_TROY_OUNCE"
SELECTION_RULE = "exact_boundary_observation"

MARKET_SECONDS = 900
SETTLEMENT_GRACE_SECONDS = 600
MAX_SETTLEMENT_ATTEMPTS = 3
MAX_GAP_SECONDS = 180
MAX_SKEW_SECONDS = 60
MAX_PRICE = 10**12
FEE_BPS = 200
BPS_DENOMINATOR = 10_000
PRICE_SCALE = 1_000_000
DEMO_CREDITS = 1_000

PENDING_REASONS = (
    "SOURCE_UNAVAILABLE",
    "FIXTURE_NOT_FOUND",
    "MALFORMED_JSON",
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

    def _require_market(self, market_id: str) -> Market:
        if not isinstance(market_id, str) or len(market_id) == 0 or len(market_id) > 96:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market id")
        if market_id not in self.markets:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market does not exist")
        return self.markets[market_id]

    def _empty_market(self, market_id: str, start_at: str, evidence_url: str) -> Market:
        end_at = self._add_seconds(start_at, MARKET_SECONDS)
        return Market(
            market_id=market_id,
            start_at=start_at,
            end_at=end_at,
            settlement_deadline=self._add_seconds(end_at, SETTLEMENT_GRACE_SECONDS),
            evidence_url=evidence_url,
            source_id=SOURCE_ID,
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

    def _require_exact_fields(self, value, fields: tuple, label: str) -> None:
        if not isinstance(value, dict):
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} {label} must be an object")
        keys = list(value.keys())
        if len(keys) != len(fields):
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} {label} has missing or unexpected fields")
        for field in fields:
            if field not in value:
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} {label} has missing or unexpected fields")

    def _evidence_hash_payload(self, evidence: dict) -> dict:
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

    def _sha256(self, value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _expected_evidence_url(self, market_id: str) -> str:
        return f"{self.source_base_url}{market_id}.json"

    def _pending_evidence(self, market: Market, reason_code: str) -> dict:
        if reason_code not in PENDING_REASONS:
            reason_code = "INVALID_SCHEMA"
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "status": "PENDING_EVIDENCE",
            "market_id": market.market_id,
            "source_id": market.source_id,
            "evidence_url": market.evidence_url,
            "currency": CURRENCY,
            "unit": UNIT,
            "selection_rule": SELECTION_RULE,
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

    def _validate_evidence_result(self, raw, market: Market) -> dict:
        self._require_exact_fields(raw, EVIDENCE_FIELDS, "evidence result")
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
            if not isinstance(raw[field], str):
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence field has invalid type")
        for field in (
            "max_gap_seconds",
            "max_skew_seconds",
            "gold_opening_price",
            "gold_closing_price",
            "silver_opening_price",
            "silver_closing_price",
        ):
            if isinstance(raw[field], bool) or not isinstance(raw[field], int):
                raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence numeric field has invalid type")
        if raw["schema_version"] != EVIDENCE_SCHEMA_VERSION:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} unsupported evidence schema")
        if raw["market_id"] != market.market_id or raw["source_id"] != market.source_id:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence market identity mismatch")
        if raw["evidence_url"] != market.evidence_url:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence URL is not frozen")
        if raw["currency"] != CURRENCY or raw["unit"] != UNIT:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} currency or unit mismatch")
        if raw["selection_rule"] != SELECTION_RULE:
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
            for field in (
                "max_gap_seconds",
                "max_skew_seconds",
                "gold_opening_price",
                "gold_closing_price",
                "silver_opening_price",
                "silver_closing_price",
            ):
                if raw[field] != 0:
                    raise gl.vm.UserError(f"{ERROR_CONSENSUS} pending evidence contains data")
            return raw
        if raw["status"] != "FINALIZED" or raw["reason_code"] != "NONE":
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} unsupported evidence status")
        if raw["max_gap_seconds"] < 0 or raw["max_gap_seconds"] > MAX_GAP_SECONDS:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} observation gap exceeds frozen limit")
        if raw["max_skew_seconds"] < 0 or raw["max_skew_seconds"] > MAX_SKEW_SECONDS:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} timestamp skew exceeds frozen limit")
        if raw["gold_opening_timestamp"] != market.start_at or raw["silver_opening_timestamp"] != market.start_at:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} opening timestamps are inconsistent")
        if raw["gold_closing_timestamp"] != market.end_at or raw["silver_closing_timestamp"] != market.end_at:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} closing timestamps are inconsistent")
        for field in (
            "gold_opening_timestamp",
            "gold_closing_timestamp",
            "silver_opening_timestamp",
            "silver_closing_timestamp",
        ):
            self._validate_timestamp(raw[field], field)
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
        expected_hash = self._sha256(
            json.dumps(self._evidence_hash_payload(raw), sort_keys=True, separators=(",", ":"))
        )
        if raw["evidence_hash"] != expected_hash:
            raise gl.vm.UserError(f"{ERROR_CONSENSUS} evidence hash mismatch")
        return raw

    def _read_evidence(self, market: Market) -> dict:
        try:
            response = gl.nondet.web.get(market.evidence_url)
            body = response.body
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            parsed = json.loads(str(body))
        except Exception:
            return self._pending_evidence(market, "SOURCE_UNAVAILABLE")
        try:
            return self._validate_evidence_result(parsed, market)
        except Exception:
            return self._pending_evidence(market, "INVALID_SCHEMA")

    def _consensus_evidence(self, market: Market) -> dict:
        def leader_fn() -> dict:
            return self._read_evidence(market)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader = self._validate_evidence_result(leader_result.calldata, market)
                validator = self._read_evidence(market)
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
        if not isinstance(source_base_url, str) or not source_base_url.startswith("https://") or not source_base_url.endswith("/") or len(source_base_url) > 200:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source base URL must be an HTTPS directory")
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
        if self._timestamp_to_epoch(now) >= self._timestamp_to_epoch(start_at):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market start must be in the future")
        if market_id in self.markets:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market already exists")
        if self.current_market_id and self.current_market_id in self.markets:
            current = self.markets[self.current_market_id]
            if self._timestamp_to_epoch(now) < self._timestamp_to_epoch(current.end_at):
                raise gl.vm.UserError(f"{ERROR_EXPECTED} an active market already exists")
            if self._timestamp_to_epoch(start_at) <= self._timestamp_to_epoch(current.start_at):
                raise gl.vm.UserError(f"{ERROR_EXPECTED} market must move forward in time")
        self.markets[market_id] = self._empty_market(market_id, start_at, evidence_url)
        self.market_ids.append(market_id)
        self.current_market_id = market_id

    @gl.public.write
    def open_market(self, market_id: str, start_at: str, evidence_url: str) -> None:
        self._open_market(market_id, start_at, evidence_url)

    @gl.public.write
    def open_next_market(self) -> str:
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
        balance = self.demo_balances.get(gl.message.sender_address, 0)
        if balance < amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} insufficient demo credits")
        self.demo_balances[gl.message.sender_address] = balance - amount
        if side == SIDE_GOLD:
            market.gold_pool += amount
        else:
            market.silver_pool += amount
        market.total_staked += amount
        key = self._position_key(market_id, gl.message.sender_address, side)
        if key in self.positions:
            position = self.positions[key]
            if position.claimed:
                raise gl.vm.UserError(f"{ERROR_EXPECTED} claimed position cannot receive more stake")
            position.stake += amount
            self.positions[key] = position
        else:
            self.positions[key] = Position(
                market_id=market_id,
                owner=gl.message.sender_address,
                side=side,
                stake=amount,
                claimed=False,
                payout=0,
                entered_at=now,
            )
        self.markets[market_id] = market

    # ------------------------------------------------------------------
    # Settlement and finality-gated claims
    # ------------------------------------------------------------------

    def _market_is_final(self, market_id: str) -> bool:
        if not self.finality_gate_configured:
            return False
        try:
            record = SettlementGateInterface(self.finality_gate).view().get_finality(market_id)
            return isinstance(record, dict) and record.get("finalized") is True and record.get("market_id") == market_id
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

    @gl.public.write
    def request_settlement(self, market_id: str) -> None:
        market = self._require_market(market_id)
        now = self._transaction_time()
        if self._timestamp_to_epoch(now) < self._timestamp_to_epoch(market.end_at):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market has not ended")
        if market.outcome:
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
        market.outcome = OUTCOME_REFUND
        market.distributable_pool = market.total_staked
        market.fee_amount = 0
        market.last_reason_code = "SETTLEMENT_DEADLINE_REFUND"
        market.settlement_state = SETTLEMENT_REFUND_PROVISIONAL
        self.markets[market_id] = market
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
        if payout > 0:
            self.demo_balances[gl.message.sender_address] = self.demo_balances.get(gl.message.sender_address, 0) + payout

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
        return {
            "fee_bps": FEE_BPS,
            "fee_percent_display": "2%",
            "market_seconds": MARKET_SECONDS,
            "settlement_grace_seconds": SETTLEMENT_GRACE_SECONDS,
            "max_settlement_attempts": MAX_SETTLEMENT_ATTEMPTS,
            "max_gap_seconds": MAX_GAP_SECONDS,
            "max_skew_seconds": MAX_SKEW_SECONDS,
            "price_scale": PRICE_SCALE,
            "rounding_policy": "floor each proportional payout; dust remains undistributed",
            "refund_policy": "equal relative returns, one-sided pools, or deadline expiry refund stakes without fees",
            "source_id": SOURCE_ID,
            "source_base_url": self.source_base_url,
            "source_base_configured": self.source_base_configured,
            "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
            "rule_version": RULE_VERSION,
            "selection_rule": SELECTION_RULE,
            "gold_instrument": GOLD_INSTRUMENT,
            "silver_instrument": SILVER_INSTRUMENT,
            "currency": CURRENCY,
            "unit": UNIT,
            "synthetic_demo": True,
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
        return {"market_ids": result, "total": len(self.market_ids), "offset": offset, "limit": limit}

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
        index = offset
        scanned = 0
        while index < len(self.market_ids) and scanned < limit:
            market_id = self.market_ids[index]
            for side in SIDES:
                key = self._position_key(market_id, owner, side)
                if key in self.positions:
                    result.append(self._position_to_dict(self.positions[key]))
                    scanned += 1
                    if scanned >= limit:
                        break
            index += 1
        return {"positions": result, "total_markets": len(self.market_ids), "offset": offset, "limit": limit}

    @gl.public.view
    def get_account(self, owner: Address) -> dict:
        owner = self._normalize_address(owner)
        positions = 0
        total_staked = 0
        claimed_payouts = 0
        index = 0
        while index < len(self.market_ids):
            market_id = self.market_ids[index]
            for side in SIDES:
                key = self._position_key(market_id, owner, side)
                if key in self.positions:
                    position = self.positions[key]
                    positions += 1
                    total_staked += position.stake
                    claimed_payouts += position.payout
            index += 1
        return {
            "owner": owner.as_hex,
            "demo_balance": self.demo_balances.get(owner, 0),
            "demo_credits_claimed": self.demo_credits_claimed.get(owner, False),
            "position_count": positions,
            "total_staked": total_staked,
            "claimed_payouts": claimed_payouts,
        }

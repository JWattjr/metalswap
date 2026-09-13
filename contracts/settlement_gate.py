# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""Finality boundary for MetalSwap claims.

MetalSwap emits this record with ``on='finalized'`` after a consensus
settlement. Claims read this separate contract, so an accepted/provisional
adjudication cannot release even synthetic demo credits.
"""

from dataclasses import dataclass

from genlayer import *


ERROR_EXPECTED = "[EXPECTED]"
OUTCOMES = ("GOLD", "SILVER", "REFUND")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@allow_storage
@dataclass
class FinalityRecord:
    market_id: str
    outcome: str
    distributable_pool: u256
    fee_amount: u256
    gold_opening_price: u256
    gold_closing_price: u256
    silver_opening_price: u256
    silver_closing_price: u256
    source_url: str
    evidence_hash: str
    finalized_at: str


class SettlementGate(gl.Contract):
    owner: Address
    market_contract: Address
    market_configured: bool
    records: TreeMap[str, FinalityRecord]
    market_ids: DynArray[str]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.market_contract = gl.message.sender_address
        self.market_configured = False

    def _normalize_address(self, value: Address) -> Address:
        if isinstance(value, str):
            return Address(value)
        return value

    def _require_owner(self) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} owner authorization required")

    def _require_market(self) -> None:
        if not self.market_configured or gl.message.sender_address != self.market_contract:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} MetalSwap authorization required")

    def _transaction_time(self) -> str:
        message = getattr(gl, "message", None)
        value = getattr(message, "datetime", None)
        if value is not None:
            return str(value)
        raw = getattr(gl, "message_raw", None)
        if raw is not None and raw.get("datetime") is not None:
            return str(raw.get("datetime"))
        return "1970-01-01T00:00:00Z"

    @gl.public.write
    def configure_market(self, market_address: Address) -> None:
        self._require_owner()
        if self.market_configured:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} market already configured")
        market_address = self._normalize_address(market_address)
        if market_address.as_hex == ZERO_ADDRESS or market_address == self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market address")
        self.market_contract = market_address
        self.market_configured = True

    @gl.public.write
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
    ) -> None:
        self._require_market()
        if not isinstance(market_id, str) or len(market_id) == 0 or len(market_id) > 96:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market id")
        if outcome not in OUTCOMES:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid market outcome")
        if not isinstance(source_url, str) or len(source_url) == 0 or len(source_url) > 2_048:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid evidence URL")
        if not isinstance(evidence_hash, str) or len(evidence_hash) > 160:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid evidence hash")
        if market_id in self.records:
            current = self.records[market_id]
            if (
                current.outcome != outcome
                or current.distributable_pool != distributable_pool
                or current.fee_amount != fee_amount
                or current.gold_opening_price != gold_opening_price
                or current.gold_closing_price != gold_closing_price
                or current.silver_opening_price != silver_opening_price
                or current.silver_closing_price != silver_closing_price
                or current.source_url != source_url
                or current.evidence_hash != evidence_hash
            ):
                raise gl.vm.UserError(f"{ERROR_EXPECTED} finality record conflicts with existing record")
            return
        self.records[market_id] = FinalityRecord(
            market_id=market_id,
            outcome=outcome,
            distributable_pool=distributable_pool,
            fee_amount=fee_amount,
            gold_opening_price=gold_opening_price,
            gold_closing_price=gold_closing_price,
            silver_opening_price=silver_opening_price,
            silver_closing_price=silver_closing_price,
            source_url=source_url,
            evidence_hash=evidence_hash,
            finalized_at=self._transaction_time(),
        )
        self.market_ids.append(market_id)

    def _record_to_dict(self, record: FinalityRecord) -> dict:
        return {
            "finalized": True,
            "market_id": record.market_id,
            "outcome": record.outcome,
            "distributable_pool": record.distributable_pool,
            "fee_amount": record.fee_amount,
            "gold_opening_price": record.gold_opening_price,
            "gold_closing_price": record.gold_closing_price,
            "silver_opening_price": record.silver_opening_price,
            "silver_closing_price": record.silver_closing_price,
            "source_url": record.source_url,
            "evidence_hash": record.evidence_hash,
            "finalized_at": record.finalized_at,
        }

    @gl.public.view
    def get_finality(self, market_id: str) -> dict:
        if market_id not in self.records:
            return {"finalized": False, "market_id": market_id}
        return self._record_to_dict(self.records[market_id])

    @gl.public.view
    def get_gate_status(self) -> dict:
        return {
            "market_configured": self.market_configured,
            "market_contract": self.market_contract.as_hex,
            "finalized_markets": len(self.market_ids),
        }

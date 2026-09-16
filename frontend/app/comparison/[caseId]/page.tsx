import Link from "next/link";
import { notFound } from "next/navigation";

import realCase from "@/public/comparisons/xaus-2026-09-14-09-00-00z.json";
import liveCase from "@/public/comparisons/xaus-live-2026-09-16-12-15-00z.json";
import syntheticCase from "@/public/comparisons/metalswap-synthetic-2026-09-14-07-30-00z.json";

export const dynamic = "force-static";

const CASES = {
  [liveCase.case_id]: liveCase,
  [realCase.case_id]: realCase,
  [syntheticCase.case_id]: syntheticCase,
} as const;

type ComparisonCase = (typeof CASES)[keyof typeof CASES];
type Observation = ComparisonCase["observations"]["gold"];

function fixedPrice(value: number): string {
  const fixed = BigInt(value);
  const whole = fixed / 1_000_000n;
  const fraction = (fixed % 1_000_000n).toString().padStart(6, "0").replace(/0+$/, "");
  return `$${Number(whole).toLocaleString("en-US")}${fraction ? `.${fraction}` : ".00"}`;
}

function returnPercent(observation: Observation): string {
  const opening = BigInt(observation.opening.price_fixed);
  const delta = BigInt(observation.closing.price_fixed) - opening;
  const negative = delta < 0n;
  const absolute = negative ? -delta : delta;
  const hundredths = (absolute * 10_000n + opening / 2n) / opening;
  const whole = hundredths / 100n;
  const fraction = (hundredths % 100n).toString().padStart(2, "0");
  return `${negative ? "-" : "+"}${whole}.${fraction}%`;
}

function returnNumber(observation: Observation): number {
  return Number(BigInt(observation.closing.price_fixed) - BigInt(observation.opening.price_fixed)) / Number(observation.opening.price_fixed);
}

function proofCase(caseId: string): ComparisonCase | null {
  return CASES[caseId as keyof typeof CASES] ?? null;
}

function explorerUrl(hash: string): string {
  return `https://genlayer-explorer.vercel.app/tx/${hash}`;
}

function sourceLink(label: string, url: string) {
  return <a href={url} target="_blank" rel="noreferrer">{label} ↗</a>;
}

export async function generateStaticParams() {
  return Object.keys(CASES).map((caseId) => ({ caseId }));
}

export async function generateMetadata({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const current = proofCase(caseId);
  return { title: current ? `MetalSwap proof · ${current.case_id}` : "MetalSwap proof" };
}

export default async function ComparisonProofPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const current = proofCase(caseId);
  if (!current) notFound();

  const gold = current.observations.gold;
  const silver = current.observations.silver;
  const goldCross = BigInt(gold.closing.price_fixed) * BigInt(silver.opening.price_fixed);
  const silverCross = BigInt(silver.closing.price_fixed) * BigInt(gold.opening.price_fixed);
  const winner = goldCross === silverCross ? "REFUND" : goldCross > silverCross ? "GOLD" : "SILVER";
  const isSynthetic = current.mode === "SYNTHETIC_DEMO";
  const isLive = current.mode === "LIVE_INTERVAL";
  const settlement = current.settlement;

  return (
    <main className="comparison-page">
      <div className="comparison-shell">
        <nav className="comparison-nav" aria-label="Proof navigation">
          <Link href="/" className="comparison-brand">METALSWAP</Link>
          <span>PUBLIC COMPARISON PROOF</span>
        </nav>

        <header className="comparison-hero">
          <div>
            <span className="comparison-kicker">{isSynthetic || isLive ? "COMPLETED MARKET" : "SOURCE COMPARISON"}</span>
            <h1>{isSynthetic ? "Gold vs Silver settlement proof" : isLive ? "Gold vs Silver live-interval proof" : "Gold vs Silver real-observation replay"}</h1>
            <p>{current.note}</p>
          </div>
          <span className={`comparison-mode ${isSynthetic ? "synthetic" : "historical"}`}>
            {isSynthetic ? "SYNTHETIC DEMO" : isLive ? "INDICATIVE LIVE INTERVAL" : "HISTORICAL REPLAY"}
          </span>
        </header>

        <section className="comparison-warning" aria-label="Data mode disclosure">
          <strong>{isSynthetic ? "Predictable developer-generated evidence" : "Indicative published observations"}</strong>
          <span>{isSynthetic ? "Delayed publication does not make this outcome unpredictable." : "XAUS documents these as indicative mid-market quotes, not official benchmarks or executable prices."}</span>
        </section>

        <section className="comparison-card">
          <div className="comparison-card-heading"><div><span className="comparison-kicker">CASE</span><h2>{current.market_id}</h2></div><span className="comparison-state">{current.interval.start_at} → {current.interval.end_at}</span></div>
          <div className="comparison-table-wrap">
            <table className="comparison-table">
              <thead><tr><th>INSTRUMENT</th><th>OPENING OBSERVATION</th><th>CLOSING OBSERVATION</th><th>RELATIVE RETURN</th></tr></thead>
              <tbody>
                <tr><td><strong className="gold-text">GOLD</strong><small>{gold.instrument}</small></td><td>{fixedPrice(gold.opening.price_fixed)}<small>{gold.opening.timestamp}</small></td><td>{fixedPrice(gold.closing.price_fixed)}<small>{gold.closing.timestamp}</small></td><td className={returnNumber(gold) >= 0 ? "positive" : "negative"}>{returnPercent(gold)}</td></tr>
                <tr><td><strong className="silver-text">SILVER</strong><small>{silver.instrument}</small></td><td>{fixedPrice(silver.opening.price_fixed)}<small>{silver.opening.timestamp}</small></td><td>{fixedPrice(silver.closing.price_fixed)}<small>{silver.closing.timestamp}</small></td><td className={returnNumber(silver) >= 0 ? "positive" : "negative"}>{returnPercent(silver)}</td></tr>
              </tbody>
            </table>
          </div>
          <div className="comparison-grid"><div><small>CURRENCY / UNIT</small><strong>{gold.currency} · {gold.unit}</strong></div><div><small>SELECTION RULE</small><strong>{current.alignment.selection_rule}</strong></div><div><small>BOUNDARY STALENESS</small><strong>≤ {current.alignment.max_boundary_staleness_seconds}s allowed · {current.alignment.actual_max_boundary_staleness_seconds}s observed</strong></div><div><small>CROSS-METAL SKEW</small><strong>≤ {current.alignment.max_cross_metal_timestamp_skew_seconds}s allowed · {current.alignment.actual_max_cross_metal_timestamp_skew_seconds}s observed</strong></div></div>
        </section>

        <section className="comparison-card comparison-outcome">
          <div className="comparison-card-heading"><div><span className="comparison-kicker">DETERMINISTIC DECISION</span><h2>{winner === "REFUND" ? "Equal relative performance" : `${winner} outperformed`}</h2></div><span className="comparison-state">fixed-point scale {current.alignment.fixed_point_scale.toLocaleString()}</span></div>
          <p>Winner selection never uses floating-point returns. The contract compares the cross products directly:</p>
          <div className="cross-products"><code>gold_close × silver_open = {goldCross.toLocaleString()}</code><code>silver_close × gold_open = {silverCross.toLocaleString()}</code></div>
          <p className="comparison-explanation">{winner === "REFUND" ? "The cross products are equal, so the protocol refunds the stakes without a fee." : `${winner} wins because its relative return is higher, not because its nominal price is higher.`}</p>
        </section>

        <section className="comparison-card">
          <div className="comparison-card-heading"><div><span className="comparison-kicker">PROVENANCE</span><h2>What was fetched and frozen</h2></div></div>
          <div className="source-list"><div><strong>{current.source.name}</strong><span>Source ID: <code>{current.source.id}</code></span><span>Response state: <code>{current.source.source_state}</code> · {current.source.source_state_origin}</span><span>Captured: {current.source.captured_at}</span><span>Canonical comparison hash: <code>{current.evidence_hash}</code></span></div><div className="source-links">{sourceLink("Source terms and API policy", current.source.terms_url)}{ "gold_url" in current.source ? sourceLink("Gold response reference", current.source.gold_url) : sourceLink("Frozen evidence JSON", current.source.evidence_url)}{ "silver_url" in current.source ? sourceLink("Silver response reference", current.source.silver_url) : null}</div></div>
        </section>

        <section className="comparison-card comparison-settlement">
          <div className="comparison-card-heading"><div><span className="comparison-kicker">MARKET / FINALITY</span><h2>{settlement ? "On-chain mechanics proof" : "Comparison-only replay"}</h2></div></div>
          {settlement ? <>
            <div className="comparison-grid"><div><small>POOL</small><strong>{settlement.pool} demo credits</strong></div><div><small>FEE / DISTRIBUTABLE</small><strong>{settlement.fee} / {settlement.distributable_pool} credits</strong></div><div><small>GATE</small><strong>{settlement.gate_finalized ? "FINALIZED" : "NOT FINALIZED"}</strong></div><div><small>PAYOUT</small><strong>{settlement.payout} credits · {settlement.payout_side}</strong></div></div>
            <div className="receipt-list"><span>Settlement <a href={explorerUrl(settlement.settlement_receipt)} target="_blank" rel="noreferrer">{settlement.settlement_receipt} ↗</a></span>{"gate_receipt" in settlement ? <span>Gate acknowledgment <a href={explorerUrl(settlement.gate_receipt)} target="_blank" rel="noreferrer">{settlement.gate_receipt} ↗</a></span> : null}<span>Payout <a href={explorerUrl(settlement.payout_receipt)} target="_blank" rel="noreferrer">{settlement.payout_receipt} ↗</a></span><span>Duplicate claim rejected <a href={explorerUrl(settlement.duplicate_claim_receipt)} target="_blank" rel="noreferrer">{settlement.duplicate_claim_receipt} ↗</a></span>{"rotation_receipt" in settlement ? <span>Rotation / historical access <a href={explorerUrl(settlement.rotation_receipt)} target="_blank" rel="noreferrer">{settlement.rotation_receipt} ↗</a></span> : null}</div>
            <p className="comparison-muted">Gate finalized at {settlement.gate_finalized_at}. Duplicate claim result: <code>{settlement.duplicate_claim_error}</code>. Contract source revision: <code>{settlement.source_revision}</code>.</p>
          </> : <p className="comparison-muted">This replay intentionally has no pool, fee, payout, or finality state. It is a wallet-free comparison case only; it must not be presented as a wager or settlement.</p>}
        </section>

        <section className="falling-example"><span className="comparison-kicker">WHY RELATIVE PERFORMANCE</span><strong>Example: the metal falling less wins</strong><span>Gold 2,000 → 1,998 = −0.10%; Silver 25 → 24.75 = −1.00%; Gold outperforms because its decline is smaller.</span></section>

        <footer className="comparison-footer"><Link href="/">← Return to MetalSwap</Link><span>One pair · 15 minutes · demo-credit pari-mutuel mechanics</span></footer>
      </div>
    </main>
  );
}

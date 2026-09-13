"use client";

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Copy,
  Database,
  ExternalLink,
  Info,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  GENLAYER_RPC_URL,
  METALSWAP_ADDRESS,
  NETWORK_NAME,
  hasDeployment,
  readContract,
  writeContract,
} from "@/lib/genlayer";
import type { ContractAccount, ContractMarket, LocalPosition, ProtocolConfig, Side, TransactionState } from "@/lib/types";
import { connectWallet, getConnectedAccount, shortAddress } from "@/lib/wallet";

const GOLD = "GOLD" as const;
const SILVER = "SILVER" as const;

type SessionMode = "idle" | "local" | "contract";

interface PoolState {
  GOLD: number;
  SILVER: number;
}

interface ChartPoint {
  label: string;
  gold: number;
  silver: number;
}

const demoConfig: ProtocolConfig = {
  fee_percent_display: "2%",
  max_settlement_attempts: 3,
  settlement_grace_seconds: 600,
  max_gap_seconds: 180,
  max_skew_seconds: 60,
  price_scale: 1_000_000,
  source_id: "metalswap-synthetic-evidence-v1",
  source_base_url: "/evidence/",
  evidence_schema_version: "metalswap-evidence-v1",
  rule_version: "relative-return-cross-multiplication-v1",
  selection_rule: "exact_boundary_observation",
  gold_instrument: "SYNTHETIC-XAUUSD-SPOT",
  silver_instrument: "SYNTHETIC-XAGUSD-SPOT",
  currency: "USD",
  unit: "USD_PER_TROY_OUNCE",
  synthetic_demo: true,
  finality_gate_configured: false,
};

const replayEvidence = {
  goldOpen: 2351.42,
  goldClose: 2353.18,
  silverOpen: 28.16,
  silverClose: 28.31,
  goldReturn: 0.0748,
  silverReturn: 0.5327,
};

function isoUtc(date: Date): string {
  return date.toISOString().replace(".000Z", "Z");
}

function quarterFloor(date: Date): Date {
  const next = new Date(date);
  next.setUTCSeconds(0, 0);
  next.setUTCMinutes(Math.floor(next.getUTCMinutes() / 15) * 15);
  return next;
}

function addMinutes(date: Date, minutes: number): Date {
  return new Date(date.valueOf() + minutes * 60_000);
}

function marketId(start: Date): string {
  return `market-${isoUtc(start)}`;
}

function formatUtc(date: Date, withSeconds = false): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: false,
  }).format(date) + " UTC";
}

function formatDateUtc(date: Date): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatCredits(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function formatPrice(value: number): string {
  return new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function countdown(targetMs: number, nowMs: number): { label: string; totalSeconds: number } {
  const totalSeconds = Math.max(0, Math.floor((targetMs - nowMs) / 1000));
  const hours = Math.floor(totalSeconds / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;
  return {
    label: `${hours > 0 ? `${String(hours).padStart(2, "0")}:` : ""}${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`,
    totalSeconds,
  };
}

function makeChartSeries(): ChartPoint[] {
  return [
    { label: "−12m", gold: 100, silver: 100 },
    { label: "−10m", gold: 100.03, silver: 99.94 },
    { label: "−8m", gold: 99.98, silver: 100.08 },
    { label: "−6m", gold: 100.11, silver: 100.14 },
    { label: "−4m", gold: 100.14, silver: 100.26 },
    { label: "−2m", gold: 100.08, silver: 100.38 },
    { label: "now", gold: 100.16, silver: 100.49 },
  ];
}

function chartPoints(series: ChartPoint[], key: "gold" | "silver"): string {
  const min = 99.86;
  const max = 100.58;
  return series.map((point, index) => {
    const x = 64 + (index / (series.length - 1)) * 614;
    const y = 224 - ((point[key] - min) / (max - min)) * 178;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function normalizeRecord<T>(value: unknown): T {
  return value as T;
}

function statusLabel(status: string | undefined): string {
  if (!status) return "READING MARKET";
  return status.replaceAll("_", " ");
}

function explorerLink(hash: string): string | null {
  if (!hash.startsWith("0x")) return null;
  const base = process.env.NEXT_PUBLIC_GENLAYER_EXPLORER_URL?.trim();
  return base ? `${base.replace(/\/$/, "")}/tx/${hash}` : null;
}

export default function MetalSwapTerminal() {
  const [nowMs, setNowMs] = useState(0);
  const [mode, setMode] = useState<SessionMode>("idle");
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [localBalance, setLocalBalance] = useState<number | null>(null);
  const [localPools, setLocalPools] = useState<PoolState>({ GOLD: 0, SILVER: 0 });
  const [positions, setPositions] = useState<LocalPosition[]>([]);
  const [selectedSide, setSelectedSide] = useState<Side>(SILVER);
  const [stakeAmount, setStakeAmount] = useState(25);
  const [txState, setTxState] = useState<TransactionState>("IDLE");
  const [txHash, setTxHash] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [copied, setCopied] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [contractMarket, setContractMarket] = useState<ContractMarket | null>(null);
  const [contractAccount, setContractAccount] = useState<ContractAccount | null>(null);
  const [protocolConfig, setProtocolConfig] = useState<ProtocolConfig>(demoConfig);
  const [contractReadError, setContractReadError] = useState("");

  useEffect(() => {
    const tick = () => setNowMs(Date.now());
    tick();
    const timer = window.setInterval(tick, 1_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    getConnectedAccount().then((address) => {
      if (!cancelled && address) {
        setWalletAddress(address);
        setMode(hasDeployment() ? "contract" : "local");
      }
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const referenceNow = nowMs || Date.parse("2026-09-13T08:14:00Z");
  const currentStart = useMemo(() => quarterFloor(new Date(referenceNow)), [referenceNow]);
  const currentEnd = useMemo(() => addMinutes(currentStart, 15), [currentStart]);
  const upcomingStart = currentEnd;
  const upcomingEnd = addMinutes(upcomingStart, 15);
  const upcomingMarketId = marketId(upcomingStart);
  const chartSeries = useMemo(() => makeChartSeries(), []);
  const chartGold = chartSeries[chartSeries.length - 1].gold - 100;
  const chartSilver = chartSeries[chartSeries.length - 1].silver - 100;
  const provisionalLeader: Side = chartGold >= chartSilver ? GOLD : SILVER;

  const contractEntryMarket = contractMarket?.status === "UPCOMING" ? contractMarket : null;
  const activeMarketId = contractEntryMarket?.market_id || upcomingMarketId;
  const activeStart = contractEntryMarket?.start_at ? new Date(contractEntryMarket.start_at) : upcomingStart;
  const activeEnd = contractEntryMarket?.end_at ? new Date(contractEntryMarket.end_at) : upcomingEnd;
  const intervalStart = contractMarket?.start_at ? new Date(contractMarket.start_at) : currentStart;
  const intervalEnd = contractMarket?.end_at ? new Date(contractMarket.end_at) : currentEnd;
  const currentCountdown = countdown(intervalEnd.valueOf(), referenceNow);
  const entryCountdown = countdown(activeStart.valueOf(), referenceNow);
  const entryStatusLabel = mode === "contract" && contractMarket && !contractEntryMarket
    ? "WAITING FOR NEXT MARKET"
    : "OPEN";
  const contractPools: PoolState = {
    GOLD: contractEntryMarket?.gold_pool ?? 0,
    SILVER: contractEntryMarket?.silver_pool ?? 0,
  };
  const poolStateKnown = mode === "local" || contractEntryMarket !== null;
  const pools = mode === "local" ? localPools : contractPools;
  const totalPool = pools.GOLD + pools.SILVER;
  const opposingPool = pools[selectedSide === GOLD ? SILVER : GOLD];
  const selectedPool = pools[selectedSide];
  const projectedPool = selectedPool + stakeAmount + opposingPool;
  const projectedFee = opposingPool > 0 ? Math.floor(projectedPool * 0.02) : 0;
  const estimatedPayout = opposingPool > 0
    ? Math.floor((projectedPool - projectedFee) * stakeAmount / (selectedPool + stakeAmount))
    : stakeAmount;
  const walletBalance = mode === "contract" ? (contractAccount?.demo_balance ?? null) : localBalance;
  const hasActiveSession = mode !== "idle" && Boolean(walletAddress);
  const isEntryOpen = (mode !== "contract" || contractEntryMarket !== null) && referenceNow < activeStart.valueOf();
  const canPlace = hasActiveSession && isEntryOpen && stakeAmount > 0 && (walletBalance === null || walletBalance >= stakeAmount) && txState !== "SUBMITTED";
  const displayStatus = contractMarket?.status || (isEntryOpen ? "UPCOMING" : referenceNow < activeEnd.valueOf() ? "LIVE" : "AWAITING_SETTLEMENT");

  async function refreshContract() {
    if (!hasDeployment()) return;
    setIsRefreshing(true);
    setContractReadError("");
    try {
      const [marketValue, configValue] = await Promise.all([
        readContract("get_current_market"),
        readContract("get_protocol_config"),
      ]);
      setContractMarket(normalizeRecord<ContractMarket>(marketValue));
      setProtocolConfig({ ...demoConfig, ...normalizeRecord<ProtocolConfig>(configValue) });
      if (walletAddress && mode === "contract") {
        const accountValue = await readContract("get_account", [walletAddress]);
        setContractAccount(normalizeRecord<ContractAccount>(accountValue));
      }
    } catch (error) {
      setContractReadError(error instanceof Error ? error.message : "GenLayer read failed. Try refreshing.");
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    if (!hasDeployment()) return;
    refreshContract().catch(() => undefined);
    const timer = window.setInterval(() => refreshContract().catch(() => undefined), 30_000);
    return () => window.clearInterval(timer);
    // Refreshes are intentionally bounded; the public read is not a stream.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletAddress, mode]);

  function clearError() {
    setErrorMessage("");
    setContractReadError("");
  }

  function startLocalReplay() {
    clearError();
    setMode("local");
    setWalletAddress("local-replay");
    setLocalBalance((value) => value ?? 1_000);
    setTxState("IDLE");
  }

  async function handleConnect() {
    clearError();
    if (!hasDeployment()) {
      startLocalReplay();
      return;
    }
    try {
      const address = await connectWallet();
      setWalletAddress(address);
      setMode("contract");
      setTxState("IDLE");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Wallet connection failed.");
    }
  }

  async function runWrite(functionName: string, args: unknown[], label: string): Promise<boolean> {
    clearError();
    setTxState("SUBMITTED");
    try {
      const hash = await writeContract(functionName, args);
      setTxHash(hash);
      setTxState("DECIDED");
      return true;
    } catch (error) {
      setTxState("FAILED");
      setErrorMessage(`${label}: ${error instanceof Error ? error.message : "transaction failed"}`);
      return false;
    }
  }

  async function handleClaimCredits() {
    if (mode === "contract") {
      const success = await runWrite("claim_demo_credits", [], "Demo credit request");
      if (success) await refreshContract();
      return;
    }
    startLocalReplay();
  }

  async function handlePlacePosition() {
    if (!canPlace) return;
    if (mode === "contract") {
      const success = await runWrite("place_position", [activeMarketId, selectedSide, BigInt(stakeAmount)], "Position submission");
      if (success) {
        await refreshContract();
      }
      return;
    }
    if (localBalance !== null && localBalance < stakeAmount) {
      setErrorMessage("Your local replay balance is below this stake.");
      return;
    }
    setLocalBalance((value) => (value ?? 1_000) - stakeAmount);
    setLocalPools((value) => ({ ...value, [selectedSide]: value[selectedSide] + stakeAmount }));
    setPositions((value) => [
      {
        id: `${activeMarketId}-${selectedSide}-${Date.now()}`,
        marketId: activeMarketId,
        side: selectedSide,
        stake: stakeAmount,
        status: "LOCAL_REPLAY",
        payout: null,
        enteredAt: new Date(referenceNow).toISOString(),
      },
      ...value,
    ]);
    setTxHash("");
    setTxState("IDLE");
  }

  async function handleSettlement() {
    if (!activeMarketId || referenceNow < activeEnd.valueOf()) return;
    if (mode === "contract") {
      await runWrite("request_settlement", [activeMarketId], "Settlement request");
      return;
    }
    setErrorMessage("Local replay uses a synthetic evidence record; settlement requests are only sent to a configured contract.");
  }

  async function handleClaim(position: LocalPosition) {
    if (mode !== "contract") {
      setErrorMessage("Local replay positions are not on-chain and cannot be claimed.");
      return;
    }
    await runWrite("claim_position", [position.marketId, position.side], "Claim");
  }

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1_500);
    } catch {
      setErrorMessage("Clipboard access was blocked by the browser.");
    }
  }

  const primaryLabel = mode === "idle"
    ? "Start a local replay"
    : txState === "SUBMITTED"
      ? "Waiting for GenLayer…"
      : mode === "contract" && !contractEntryMarket
        ? "Awaiting next market"
      : `Place ${selectedSide} position`;
  const txLink = explorerLink(txHash);

  return (
    <main className="terminal-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="MetalSwap home">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span className="brand-name">MetalSwap</span>
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-context">Relative market</span>
        </div>
        <div className="topbar-actions">
          <span className="network-pill"><span className="status-dot" />{NETWORK_NAME} <span className="network-separator">/</span> {hasDeployment() ? "CONTRACT READ" : "SYNTHETIC REPLAY"}</span>
          {walletAddress ? (
            <button className="wallet-button connected" onClick={() => { setWalletAddress(null); setMode("idle"); setContractAccount(null); }}>
              <WalletCards size={15} strokeWidth={1.8} />
              {mode === "local" ? "Local replay" : shortAddress(walletAddress)}
              <ChevronDown size={14} />
            </button>
          ) : (
            <button className="wallet-button" onClick={handleConnect}>
              <WalletCards size={15} strokeWidth={1.8} />
              {hasDeployment() ? "Connect wallet" : "Start local replay"}
            </button>
          )}
        </div>
      </header>

      <section className="page-intro">
        <div>
          <h1>Gold vs Silver</h1>
          <p className="lede">Choose which benchmark will deliver the stronger percentage return over the next 15 minutes.</p>
        </div>
        <div className="truth-stack">
          <div className="truth-line"><span className="truth-dot cyan" />Synthetic evidence demo</div>
          <div className="truth-line"><LockKeyhole size={13} />2% fee frozen before entry</div>
        </div>
      </section>

      {(errorMessage || contractReadError) && (
        <div className="error-strip" role="alert">
          <AlertTriangle size={16} />
          <span>{errorMessage || contractReadError}</span>
          <button onClick={() => { clearError(); refreshContract().catch(() => undefined); }} aria-label="Dismiss error"><Check size={14} /></button>
        </div>
      )}

      <section className="interval-bar" aria-label="Interval status">
        <div className="interval-main">
          <div className="section-label">CURRENT INTERVAL</div>
          <div className="interval-time"><strong>{formatUtc(intervalStart)}</strong><span>→</span><strong>{formatUtc(intervalEnd)}</strong></div>
          <span className="utc-date">{formatDateUtc(intervalStart)}</span>
        </div>
        <div className="interval-state"><span className="live-indicator" /><span>{statusLabel(displayStatus)}</span><span className="provisional-tag">PROVISIONAL LEADER</span><strong className={provisionalLeader === GOLD ? "gold-text" : "silver-text"}>{provisionalLeader}</strong></div>
        <div className="interval-countdown">
          <Clock3 size={15} />
          <span className="countdown-label">ENDS IN</span>
          <strong>{currentCountdown.label}</strong>
          <span className="countdown-note">UTC</span>
        </div>
      </section>

      <section className="workbench">
        <div className="chart-column">
          <section className="panel chart-panel">
            <div className="panel-heading chart-heading">
              <div>
                <h2>Relative performance</h2>
                <p>Rebased to 100.00 at interval open <span className="muted-separator">·</span> display only</p>
              </div>
              <div className="chart-meta"><span className="synthetic-tag">SYNTHETIC REPLAY</span><span className="refresh-readout"><span className="status-dot warm" />sampled moments ago</span></div>
            </div>
            <div className="chart-legend" aria-label="Chart legend">
              <span className="legend-item"><span className="legend-line gold-line" /> GOLD <strong>{formatPercent(chartGold)}</strong></span>
              <span className="legend-item"><span className="legend-line silver-line" /> SILVER <strong>{formatPercent(chartSilver)}</strong></span>
              <span className="legend-explainer"><Info size={13} /> Leader is provisional until evidence is accepted</span>
            </div>
            <div className="chart-wrap">
              <svg className="performance-chart" viewBox="0 0 720 280" role="img" aria-label="Synthetic rebased relative performance for gold and silver">
                {[46, 90, 134, 178, 222].map((y) => <line key={y} className="chart-grid-line" x1="64" x2="678" y1={y} y2={y} />)}
                <line className="chart-axis-line" x1="64" x2="678" y1="224" y2="224" />
                <text x="10" y="50">100.6</text>
                <text x="10" y="94">100.4</text>
                <text x="10" y="138">100.2</text>
                <text x="10" y="182">100.0</text>
                <text x="10" y="226">99.8</text>
                <polyline className="chart-gold" points={chartPoints(chartSeries, "gold")} />
                <polyline className="chart-silver" points={chartPoints(chartSeries, "silver")} />
                <circle className="chart-end-gold" cx="678" cy={(224 - ((chartSeries[chartSeries.length - 1].gold - 99.86) / (100.58 - 99.86)) * 178).toFixed(1)} r="4" />
                <circle className="chart-end-silver" cx="678" cy={(224 - ((chartSeries[chartSeries.length - 1].silver - 99.86) / (100.58 - 99.86)) * 178).toFixed(1)} r="4" />
                {chartSeries.map((point, index) => <text key={point.label} className="chart-x-label" x={64 + (index / (chartSeries.length - 1)) * 614} y="258" textAnchor={index === 0 ? "start" : index === chartSeries.length - 1 ? "end" : "middle"}>{point.label}</text>)}
              </svg>
            </div>
            <div className="chart-footnote"><span><Database size={13} /> Chart feed: synthetic interval replay</span><span>Settlement source is independently fetched after expiry</span></div>
          </section>

          <section className="panel reading-panel">
            <div className="panel-heading compact-heading">
              <div><h2>Live reading</h2><p>Directional context only — this does not settle the market.</p></div>
              <span className="reading-chip"><span className="status-dot" /> {provisionalLeader} ahead</span>
            </div>
            <div className="reading-grid">
              <div className="reading-cell gold-reading"><div className="metal-heading"><span className="metal-swatch gold-swatch" /><span>GOLD</span><span className="instrument-code">XAU / USD</span></div><strong>{formatPercent(chartGold)}</strong><span>rebased return</span></div>
              <div className="reading-divider" />
              <div className="reading-cell silver-reading"><div className="metal-heading"><span className="metal-swatch silver-swatch" /><span>SILVER</span><span className="instrument-code">XAG / USD</span></div><strong>{formatPercent(chartSilver)}</strong><span>rebased return</span></div>
              <div className="reading-callout"><span className="callout-kicker">INTERVAL CLOSES</span><strong>{formatUtc(currentEnd)}</strong><span>Outcome remains provisional until GenLayer verifies four boundary observations.</span></div>
            </div>
          </section>
        </div>

        <aside className="panel entry-panel" aria-labelledby="entry-heading">
          <div className="entry-topline"><span className="section-label">UPCOMING MARKET</span><span className={`entry-status ${entryStatusLabel !== "OPEN" ? "waiting" : ""}`}><span className="status-dot" /> {entryStatusLabel}</span></div>
          <div className="entry-date"><strong>{formatDateUtc(activeStart)}</strong><span>{formatUtc(activeStart)} → {formatUtc(activeEnd)}</span></div>
          <div className="entry-countdown"><span>ENTRY CLOSES IN</span><strong>{entryCountdown.label}</strong><small>Quarter-hour lock · UTC</small></div>

          <div className="entry-rule" />
          <div className="section-label">CHOOSE A POSITION</div>
          <div className="side-switch" role="group" aria-label="Position selection">
            <button className={`side-option gold-option ${selectedSide === GOLD ? "selected" : ""}`} onClick={() => setSelectedSide(GOLD)} aria-pressed={selectedSide === GOLD}>
              <span className="side-option-top"><span className="metal-swatch gold-swatch" />GOLD</span><strong>OUTPERFORMS</strong><span className="side-option-note">{poolStateKnown ? `${formatCredits(pools.GOLD)} credits in pool` : "pool not read"}</span>
            </button>
            <button className={`side-option silver-option ${selectedSide === SILVER ? "selected" : ""}`} onClick={() => setSelectedSide(SILVER)} aria-pressed={selectedSide === SILVER}>
              <span className="side-option-top"><span className="metal-swatch silver-swatch" />SILVER</span><strong>OUTPERFORMS</strong><span className="side-option-note">{poolStateKnown ? `${formatCredits(pools.SILVER)} credits in pool` : "pool not read"}</span>
            </button>
          </div>

          <div className="pool-summary">
            <div><span>GOLD POOL</span><strong>{poolStateKnown ? formatCredits(pools.GOLD) : "—"}</strong></div>
            <div className="pool-bar"><span className="pool-gold-fill" style={{ width: `${totalPool > 0 ? `${(pools.GOLD / totalPool) * 100}%` : "50%"}` }} /><span className="pool-silver-fill" style={{ width: `${totalPool > 0 ? `${(pools.SILVER / totalPool) * 100}%` : "50%"}` }} /></div>
            <div><span>SILVER POOL</span><strong>{poolStateKnown ? formatCredits(pools.SILVER) : "—"}</strong></div>
          </div>

          <div className="stake-block">
            <div className="stake-heading"><span>STAKE AMOUNT</span><span>DEMO CREDITS</span></div>
            <div className="stake-input-wrap"><input aria-label="Stake amount in demo credits" type="number" min="1" step="1" value={stakeAmount} onChange={(event) => setStakeAmount(Math.max(1, Number(event.target.value) || 1))} /><span>credits</span></div>
            <div className="quick-stakes">{[10, 25, 50, 100].map((amount) => <button key={amount} className={amount === stakeAmount ? "active" : ""} onClick={() => setStakeAmount(amount)}>{amount}</button>)}</div>
          </div>

          <div className="estimate-row"><div><span>ESTIMATED PAYOUT</span><strong>{formatCredits(estimatedPayout)} credits</strong></div><span className="variable-label">variable until lock</span></div>
          <div className="payout-note">{opposingPool > 0 ? `2% fee applied to a two-sided pool · your share is proportional to your ${selectedSide} stake.` : "One-sided pool → your stake refunds without a fee if no opposing side funds."}</div>

          {!hasActiveSession ? (
            <button className="primary-action" onClick={handleConnect}><WalletCards size={17} />{primaryLabel}<ArrowUpRight size={16} /></button>
          ) : walletBalance === null ? (
            <button className="primary-action" onClick={handleClaimCredits} disabled={txState === "SUBMITTED"}><Database size={17} />Request 1,000 demo credits<ArrowUpRight size={16} /></button>
          ) : (
            <button className="primary-action" onClick={handlePlacePosition} disabled={!canPlace}><ArrowUpRight size={17} />{primaryLabel}<span className="action-key">↵</span></button>
          )}
          <p className="action-disclosure"><ShieldCheck size={13} /> Demo credits only. No leverage, liquidation, custody, or physical metal ownership.</p>
        </aside>
      </section>

      <section className="lower-grid">
        <section className="panel positions-panel">
          <div className="panel-heading compact-heading"><div><h2>My positions</h2><p>Wallet-linked entries and claim availability.</p></div><span className="position-count">{positions.length + (contractAccount?.position_count ?? 0)} total</span></div>
          {positions.length === 0 && !contractAccount?.position_count ? (
            <div className="empty-state"><div className="empty-icon"><WalletCards size={18} /></div><div><strong>No positions yet</strong><span>Choose GOLD or SILVER above to commit a prediction position for the upcoming interval.</span></div></div>
          ) : (
            <div className="position-list">
              {positions.map((position) => <div className="position-row" key={position.id}><div className={`position-token ${position.side.toLowerCase()}`}><span className={`metal-swatch ${position.side === GOLD ? "gold-swatch" : "silver-swatch"}`} />{position.side}</div><div><strong>{formatCredits(position.stake)} credits</strong><span>{position.status === "LOCAL_REPLAY" ? "Local replay · not on-chain" : "Submitted to GenLayer"}</span></div><div className="position-state"><span className="state-dot" />{position.status === "LOCAL_REPLAY" ? "LOCAL" : "SUBMITTED"}</div><button className="text-action" onClick={() => handleClaim(position)} disabled={position.status === "LOCAL_REPLAY"}>Claim<ArrowUpRight size={13} /></button></div>)}
              {contractAccount?.position_count ? <div className="position-row contract-summary"><div className="position-token contract"><LockKeyhole size={14} />CHAIN</div><div><strong>{contractAccount.position_count} contract position{contractAccount.position_count === 1 ? "" : "s"}</strong><span>{formatCredits(contractAccount.total_staked)} credits staked</span></div><div className="position-state"><span className="state-dot cyan" />READ FROM RPC</div><button className="text-action" onClick={refreshContract} disabled={isRefreshing}>{isRefreshing ? "Reading…" : "Refresh"}<RefreshCw size={13} /></button></div> : null}
            </div>
          )}
          {txHash && <div className="tx-notice"><span className="state-dot cyan" /><span>Transaction submitted · {txState === "DECIDED" ? "awaiting finality" : "processing"}</span>{txLink ? <a href={txLink} target="_blank" rel="noreferrer">View receipt <ExternalLink size={12} /></a> : <button onClick={() => copyText(txHash)}>{copied ? "Copied" : "Copy hash"} {copied ? <Check size={12} /> : <Copy size={12} />}</button>}</div>}
        </section>

        <section className="panel history-panel">
          <div className="panel-heading compact-heading"><div><h2>Settlement history</h2><p>Public finality records, when available.</p></div><span className="history-filter">ALL MARKETS <ChevronDown size={13} /></span></div>
          <div className="history-empty"><div className="history-orbit"><Database size={18} /></div><strong>No finalized history read</strong><span>Real settlement records will appear here after a protocol-finalized market is indexed. The current chart is synthetic and is not a trade history.</span></div>
        </section>
      </section>

      <section className="protocol-strip">
        <div className="protocol-title"><span className="protocol-icon"><ShieldCheck size={16} /></span><div><strong>Evidence & finality</strong><span>Every outcome follows a separately readable protocol path.</span></div></div>
        <div className="protocol-steps"><span><b>01</b>Expiry</span><ArrowDownRight size={14} /><span><b>02</b>GenLayer verifies four prices</span><ArrowDownRight size={14} /><span><b>03</b>Finality gate</span><ArrowDownRight size={14} /><span><b>04</b>Claim / refund</span></div>
        <button className="details-link" onClick={() => document.getElementById("settlement-detail")?.scrollIntoView({ behavior: "smooth" })}>Read settlement detail <ArrowUpRight size={14} /></button>
      </section>

      <section id="settlement-detail" className="settlement-detail">
        <div className="detail-heading"><div><h2>What gets verified at settlement</h2><p>Illustrative synthetic record — not live market evidence.</p></div><span className="synthetic-tag">SYNTHETIC REPLAY · NOT LIVE</span></div>
        <div className="detail-layout">
          <div className="evidence-table-wrap">
            <table className="evidence-table"><thead><tr><th>BENCHMARK</th><th>OPEN</th><th>CLOSE</th><th>RETURN</th></tr></thead><tbody><tr><td><span className="metal-swatch gold-swatch" />GOLD <small>XAU / USD</small></td><td>{formatPrice(replayEvidence.goldOpen)}</td><td>{formatPrice(replayEvidence.goldClose)}</td><td className="gold-text">{formatPercent(replayEvidence.goldReturn)}</td></tr><tr><td><span className="metal-swatch silver-swatch" />SILVER <small>XAG / USD</small></td><td>{formatPrice(replayEvidence.silverOpen)}</td><td>{formatPrice(replayEvidence.silverClose)}</td><td className="silver-text">{formatPercent(replayEvidence.silverReturn)}</td></tr></tbody></table>
            <div className="table-footnote"><Clock3 size={13} /> Both observations are selected at the exact frozen UTC boundaries. Values are shown in USD per troy ounce.</div>
          </div>
          <div className="outcome-card"><span className="section-label">ILLUSTRATIVE OUTCOME</span><div className="outcome-name silver-text">SILVER <span>OUTPERFORMS</span></div><p>GenLayer agrees on the evidence fields. Deterministic code compares:</p><code>silver_close × gold_open<br /><strong>&gt; gold_close × silver_open</strong></code><div className="outcome-note"><ShieldCheck size={14} /><span>Finality status: <strong>example only</strong><br />Claims remain gated until protocol finality.</span></div></div>
        </div>
        <div className="rule-grid"><div><span>FROZEN SOURCE ID</span><strong>{protocolConfig.source_id}</strong></div><div><span>RULE VERSION</span><strong>{protocolConfig.rule_version}</strong></div><div><span>OBSERVATION WINDOW</span><strong>exact boundary · ≤{protocolConfig.max_gap_seconds}s gap</strong></div><div><span>CONFLICT PATH</span><strong>PENDING EVIDENCE → fee-free refund</strong></div></div>
      </section>

      <footer className="footer-bar"><span>MetalSwap · GenLayer testnet prototype</span><span className="footer-links"><a href="https://docs.genlayer.com/" target="_blank" rel="noreferrer">GenLayer docs <ExternalLink size={12} /></a><a href="https://xaus.com/api/" target="_blank" rel="noreferrer">Source feasibility <ExternalLink size={12} /></a><span className="footer-rpc">{GENLAYER_RPC_URL || "RPC not configured"}</span></span></footer>
    </main>
  );
}

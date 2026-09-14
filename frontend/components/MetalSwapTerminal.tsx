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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  GENLAYER_RPC_URL,
  NETWORK_NAME,
  WrongNetworkError,
  assertWalletNetwork,
  getExpectedChainId,
  getConfiguredChain,
  hasDeployment,
  normalizeContractValue,
  readContract,
  switchToConfiguredNetwork,
  waitForFinalizedTransaction,
  writeContract,
} from "@/lib/genlayer";
import type {
  ChainPositionView,
  ContractAccount,
  ContractMarket,
  ContractMarketPage,
  ContractNumber,
  ContractPosition,
  ContractPositionPage,
  ClaimQuote,
  LocalPosition,
  ProtocolConfig,
  Side,
  TransactionState,
} from "@/lib/types";
import {
  connectWallet,
  getConnectedAccount,
  getWalletChainId,
  hasWalletProvider,
  shortAddress,
  subscribeToWalletEvents,
  walletEventAccount,
} from "@/lib/wallet";

const GOLD = "GOLD" as const;
const SILVER = "SILVER" as const;
const U256_MAX = (1n << 256n) - 1n;
const POSITION_PAGE_SIZE = 20n;
const HISTORY_PAGE_SIZE = 25n;

type SessionMode = "idle" | "local" | "contract";

interface PoolState {
  GOLD: bigint;
  SILVER: bigint;
}

interface ChartPoint {
  label: string;
  gold: number;
  silver: number;
}

const demoConfig: ProtocolConfig = {
  fee_percent_display: "2%",
  max_settlement_attempts: 3,
  max_market_horizon_seconds: 1_800,
  settlement_grace_seconds: 600,
  max_gap_seconds: 180,
  max_skew_seconds: 60,
  price_scale: 1_000_000,
  source_id: "metalswap-synthetic-evidence-v1",
  source_base_url: "/evidence/",
  source_base_configured: false,
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

function formatUtc(date: Date | null, withSeconds = false): string {
  if (!date || Number.isNaN(date.valueOf())) return "—";
  return `${new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: false,
  }).format(date)} UTC`;
}

function formatDateUtc(date: Date | null): string {
  if (!date || Number.isNaN(date.valueOf())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function toBigInt(value: ContractNumber | null | undefined): bigint | null {
  if (value === null || value === undefined || value === "") return null;
  try {
    return typeof value === "bigint" ? value : BigInt(value);
  } catch {
    return null;
  }
}

function toSafeNumber(value: ContractNumber | null | undefined, fallback = 0): number {
  const amount = toBigInt(value);
  if (amount === null || amount > BigInt(Number.MAX_SAFE_INTEGER)) return fallback;
  return Number(amount);
}

function formatCredits(value: ContractNumber | null | undefined): string {
  const amount = toBigInt(value);
  if (amount === null) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount);
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

function statusLabel(status: string | undefined): string {
  if (!status) return "READING MARKET";
  return status.replaceAll("_", " ");
}

function explorerLink(hash: string): string | null {
  if (!hash.startsWith("0x")) return null;
  const base = process.env.NEXT_PUBLIC_GENLAYER_EXPLORER_URL?.trim();
  return base ? `${base.replace(/\/$/, "")}/tx/${hash}` : null;
}

function parseStake(value: string): { amount: bigint | null; error: string } {
  if (!value.trim()) return { amount: null, error: "Enter a whole-number stake." };
  if (!/^\d+$/.test(value)) return { amount: null, error: "Stake must be a whole number of demo credits." };
  try {
    const amount = BigInt(value);
    if (amount <= 0n) return { amount: null, error: "Stake must be greater than zero." };
    if (amount > U256_MAX) return { amount: null, error: "Stake is larger than the contract limit." };
    return { amount, error: "" };
  } catch {
    return { amount: null, error: "Enter a valid whole-number stake." };
  }
}

function dateFrom(value: string | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? null : parsed;
}

function isAfter(value: string | undefined, referenceNow: number): boolean {
  const date = dateFrom(value);
  return Boolean(date && date.valueOf() <= referenceNow);
}

function record<T>(value: unknown): T {
  return normalizeContractValue(value) as T;
}

function rawList(value: unknown, key: string): unknown[] {
  if (!value || typeof value !== "object") return [];
  const candidate = (value as Record<string, unknown>)[key];
  return Array.isArray(candidate) ? candidate : [];
}

export default function MetalSwapTerminal() {
  const [nowMs, setNowMs] = useState(0);
  const [mode, setMode] = useState<SessionMode>("idle");
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [localBalance, setLocalBalance] = useState<bigint | null>(null);
  const [localPools, setLocalPools] = useState<PoolState>({ GOLD: 0n, SILVER: 0n });
  const [localPositions, setLocalPositions] = useState<LocalPosition[]>([]);
  const [contractPositions, setContractPositions] = useState<ChainPositionView[]>([]);
  const [positionNextOffset, setPositionNextOffset] = useState(0n);
  const [positionsHaveMore, setPositionsHaveMore] = useState(false);
  const [historyMarkets, setHistoryMarkets] = useState<ContractMarket[]>([]);
  const [historyNextOffset, setHistoryNextOffset] = useState(0n);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyReadState, setHistoryReadState] = useState<"loading" | "ready" | "empty" | "unavailable">("loading");
  const [historyReadError, setHistoryReadError] = useState("");
  const [selectedHistoryMarketId, setSelectedHistoryMarketId] = useState("");
  const [selectedHistoryPositionViews, setSelectedHistoryPositionViews] = useState<ChainPositionView[]>([]);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);
  const [selectedSide, setSelectedSide] = useState<Side>(SILVER);
  const [stakeAmount, setStakeAmount] = useState("25");
  const [txState, setTxState] = useState<TransactionState>("IDLE");
  const [txHash, setTxHash] = useState("");
  const [txLabel, setTxLabel] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [copied, setCopied] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [contractMarket, setContractMarket] = useState<ContractMarket | null>(null);
  const [contractAccount, setContractAccount] = useState<ContractAccount | null>(null);
  const [protocolConfig, setProtocolConfig] = useState<ProtocolConfig>(demoConfig);
  const [contractReadError, setContractReadError] = useState("");
  const [wrongNetwork, setWrongNetwork] = useState(false);
  const refreshInFlight = useRef<Promise<void> | null>(null);

  useEffect(() => {
    const tick = () => setNowMs(Date.now());
    tick();
    const timer = window.setInterval(tick, 1_000);
    return () => window.clearInterval(timer);
  }, []);

  const syncWallet = useCallback(async () => {
    const address = await getConnectedAccount();
    if (!address) return;
    setWalletAddress(address);
    setMode(hasDeployment() ? "contract" : "local");
    if (!hasDeployment()) setLocalBalance((value) => value ?? 1_000n);
  }, []);

  useEffect(() => {
    let cancelled = false;
    syncWallet().catch(() => undefined);
    const unsubscribe = subscribeToWalletEvents({
      accountsChanged: (value) => {
        if (cancelled) return;
        const address = walletEventAccount(value);
        setContractAccount(null);
        setContractPositions([]);
        setPositionNextOffset(0n);
        setPositionsHaveMore(false);
        setSelectedHistoryPositionViews([]);
        setTxState("IDLE");
        setTxHash("");
        if (!address) {
          setWalletAddress(null);
          setMode("idle");
          return;
        }
        setWalletAddress(address);
        setMode(hasDeployment() ? "contract" : "local");
        if (!hasDeployment()) setLocalBalance((value) => value ?? 1_000n);
      },
      chainChanged: () => {
        getWalletChainId().then((chainId) => {
          if (cancelled) return;
          const matches = chainId === getExpectedChainId();
          setWrongNetwork(!matches);
          setContractAccount(null);
          setContractPositions([]);
          setPositionNextOffset(0n);
          setPositionsHaveMore(false);
          if (matches) {
            setErrorMessage("");
            setStatusMessage("Wallet is back on the configured GenLayer network.");
          } else {
            setErrorMessage(`Wallet network changed. Switch to ${getConfiguredChain().name} (chain ${getExpectedChainId()}) before writing.`);
          }
        }).catch(() => {
          if (!cancelled) setWrongNetwork(true);
        });
      },
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [syncWallet]);

  // Keep the first server/client render identical; the clock effect below
  // immediately replaces the epoch placeholder after hydration.
  const referenceNow = nowMs;
  const currentStart = useMemo(() => quarterFloor(new Date(referenceNow)), [referenceNow]);
  const currentEnd = useMemo(() => addMinutes(currentStart, 15), [currentStart]);
  const upcomingStart = currentEnd;
  const upcomingEnd = addMinutes(upcomingStart, 15);
  const upcomingMarketId = marketId(upcomingStart);
  const chartSeries = useMemo(() => makeChartSeries(), []);
  const chartGold = chartSeries[chartSeries.length - 1].gold - 100;
  const chartSilver = chartSeries[chartSeries.length - 1].silver - 100;
  const provisionalLeader: Side = chartGold >= chartSilver ? GOLD : SILVER;

  const contractEntryMarket = mode === "contract" && contractMarket?.status === "UPCOMING" ? contractMarket : null;
  const localEntryMarket = mode === "local" ? {
    market_id: upcomingMarketId,
    start_at: upcomingStart.toISOString(),
    end_at: upcomingEnd.toISOString(),
    status: "UPCOMING",
  } satisfies ContractMarket : null;
  const entryMarket = contractEntryMarket ?? localEntryMarket;
  const entryContextMarket = mode !== "local" && contractMarket?.exists !== false ? contractMarket : entryMarket;
  const activeMarketId = entryMarket?.market_id ?? upcomingMarketId;
  const activeStart = dateFrom(entryMarket?.start_at) ?? upcomingStart;
  const activeEnd = dateFrom(entryMarket?.end_at) ?? upcomingEnd;
  const intervalStart = dateFrom(mode !== "local" ? contractMarket?.start_at : localEntryMarket?.start_at) ?? currentStart;
  const intervalEnd = dateFrom(mode !== "local" ? contractMarket?.end_at : localEntryMarket?.end_at) ?? currentEnd;
  const currentCountdown = countdown(intervalEnd.valueOf(), referenceNow);
  const entryCountdown = countdown(activeStart.valueOf(), referenceNow);
  const entryIsOpen = Boolean(entryMarket && referenceNow < activeStart.valueOf());
  const walletIsMarketOperator = Boolean(
    walletAddress
      && protocolConfig.owner
      && walletAddress.toLowerCase() === protocolConfig.owner.toLowerCase(),
  );
  const contractCanOpenNext = mode === "contract"
    && walletIsMarketOperator
    && !contractEntryMarket
    && ["AWAITING_SETTLEMENT", "PENDING_EVIDENCE", "AWAITING_FINALITY", "CLAIMABLE", "REFUND"].includes(contractMarket?.status ?? "");
  const entryStatusLabel = mode === "local"
    ? "OPEN"
    : contractEntryMarket
      ? "OPEN"
      : mode === "contract"
        ? contractMarket?.status === "LIVE" ? "ENTRY CLOSED" : "WAITING FOR NEXT MARKET"
        : hasDeployment() ? "CONNECT TO ENTER" : "REPLAY AVAILABLE";
  const entryHeadingLabel = mode === "local" || contractEntryMarket ? "UPCOMING MARKET" : "MARKET ACCESS";
  const contractPools: PoolState = {
    GOLD: toBigInt(contractEntryMarket?.gold_pool) ?? 0n,
    SILVER: toBigInt(contractEntryMarket?.silver_pool) ?? 0n,
  };
  const poolStateKnown = mode === "local" || contractEntryMarket !== null;
  const pools = mode === "local" ? localPools : contractPools;
  const totalPool = pools.GOLD + pools.SILVER;
  const parsedStake = parseStake(stakeAmount);
  const stakeError = parsedStake.error;
  const stakeValue = parsedStake.amount ?? 0n;
  const opposingPool = pools[selectedSide === GOLD ? SILVER : GOLD];
  const selectedPool = pools[selectedSide];
  const projectedPool = selectedPool + stakeValue + opposingPool;
  const projectedFee = opposingPool > 0n ? (projectedPool * 20n) / 1_000n : 0n;
  const estimatedPayout = opposingPool > 0n && selectedPool + stakeValue > 0n
    ? ((projectedPool - projectedFee) * stakeValue) / (selectedPool + stakeValue)
    : stakeValue;
  const walletBalance = mode === "contract" ? toBigInt(contractAccount?.demo_balance) : localBalance;
  const hasActiveSession = mode !== "idle" && Boolean(walletAddress);
  const txBusy = txState === "SUBMITTED" || txState === "PROVISIONAL";
  const isEntryOpen = entryIsOpen && (mode === "local" || mode === "contract");
  const canPlacePosition = hasActiveSession
    && isEntryOpen
    && !stakeError
    && stakeValue > 0n
    && (walletBalance === null || walletBalance >= stakeValue)
    && !wrongNetwork
    && !txBusy;
  const displayStatus = mode === "local"
    ? (isEntryOpen ? "UPCOMING" : referenceNow < activeEnd.valueOf() ? "LIVE" : "AWAITING_SETTLEMENT")
    : contractMarket?.status || (hasDeployment() ? "READING MARKET" : "SYNTHETIC REPLAY");
  const selectedHistoryMarket = useMemo(
    () => historyMarkets.find((market) => market.market_id === selectedHistoryMarketId) ?? null,
    [historyMarkets, selectedHistoryMarketId],
  );

  const enrichPositions = useCallback(async (
    rawPositions: ContractPosition[],
    owner: string,
  ): Promise<ChainPositionView[]> => Promise.all(rawPositions.map(async (position): Promise<ChainPositionView> => {
    if (!position.market_id || !position.side) return { position, market: null, quote: null };
    try {
      const [positionMarket, quoteValue] = await Promise.all([
        readContract("get_market", [position.market_id]),
        readContract("get_claim_quote", [position.market_id, owner, position.side]),
      ]);
      return {
        position,
        market: record<ContractMarket>(positionMarket),
        quote: record<ClaimQuote>(quoteValue),
      };
    } catch {
      return { position, market: null, quote: null };
    }
  })), []);

  const loadHistoryPage = useCallback(async (offset: bigint, append: boolean) => {
    setHistoryReadState("loading");
    if (!append) setHistoryReadError("");
    try {
      const pageValue = await readContract("get_market_ids", [offset, HISTORY_PAGE_SIZE]);
      const page = record<ContractMarketPage>(pageValue);
      const ids = rawList(pageValue, "market_ids")
        .filter((value): value is string => typeof value === "string");
      const markets = await Promise.all(ids.map(async (id) => {
        try {
          return record<ContractMarket>(await readContract("get_market", [id]));
        } catch {
          return null;
        }
      }));
      const resolved = markets.filter((value): value is ContractMarket => Boolean(value?.market_id));
      setHistoryMarkets((current) => {
        const merged = append ? [...current] : [];
        const seen = new Set(merged.map((market) => market.market_id));
        for (const market of resolved) {
          if (market.market_id && !seen.has(market.market_id)) merged.push(market);
        }
        return merged;
      });
      const nextOffset = toBigInt(page.next_offset) ?? offset + BigInt(ids.length);
      const total = toBigInt(page.total);
      setHistoryNextOffset(nextOffset);
      setHistoryHasMore(page.has_more ?? (total !== null && nextOffset < total));
      setHistoryReadState(offset === 0n && resolved.length === 0 ? "empty" : "ready");
    } catch (error) {
      setHistoryReadState("unavailable");
      setHistoryReadError(error instanceof Error ? error.message : "On-chain market history is unavailable.");
    }
  }, []);

  const refreshContract = useCallback(async () => {
    if (!hasDeployment()) return;
    if (refreshInFlight.current) return refreshInFlight.current;
    const task = (async () => {
      setIsRefreshing(true);
      setContractReadError("");
      try {
        const [marketValue, configValue] = await Promise.all([
          readContract("get_current_market"),
          readContract("get_protocol_config"),
        ]);
        const market = record<ContractMarket>(marketValue);
        setContractMarket(market);
        setProtocolConfig({ ...demoConfig, ...record<ProtocolConfig>(configValue) });
        await loadHistoryPage(0n, false);
        if (walletAddress && mode === "contract") {
          await assertWalletNetwork();
          setWrongNetwork(false);
          const [accountValue, positionsValue] = await Promise.all([
            readContract("get_account", [walletAddress]),
            readContract("get_user_positions", [walletAddress, 0n, POSITION_PAGE_SIZE]),
          ]);
          const account = record<ContractAccount>(accountValue);
          const positionPage = record<ContractPositionPage>(positionsValue);
          const rawPositions = rawList(positionsValue, "positions").map((value) => record<ContractPosition>(value));
          const enriched = await enrichPositions(rawPositions, walletAddress);
          setContractAccount(account);
          setContractPositions(enriched);
          setPositionNextOffset(toBigInt(positionPage.next_offset) ?? BigInt(rawPositions.length));
          setPositionsHaveMore(Boolean(positionPage.has_more));
        } else if (mode !== "contract") {
          setContractAccount(null);
          setContractPositions([]);
          setPositionNextOffset(0n);
          setPositionsHaveMore(false);
        }
      } catch (error) {
        if (error instanceof WrongNetworkError) {
          setWrongNetwork(true);
          setContractAccount(null);
          setContractPositions([]);
          setErrorMessage(error.message);
        } else {
          setContractReadError(error instanceof Error ? error.message : "GenLayer read failed. Try refreshing.");
        }
      } finally {
        setIsRefreshing(false);
      }
    })();
    refreshInFlight.current = task;
    try {
      await task;
    } finally {
      if (refreshInFlight.current === task) refreshInFlight.current = null;
    }
  }, [enrichPositions, loadHistoryPage, mode, walletAddress]);

  useEffect(() => {
    if (!hasDeployment()) return;
    refreshContract().catch(() => undefined);
    const timer = window.setInterval(() => refreshContract().catch(() => undefined), 30_000);
    return () => window.clearInterval(timer);
  }, [refreshContract]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedHistoryMarketId || mode !== "contract" || !walletAddress) {
      setSelectedHistoryPositionViews([]);
      setHistoryDetailLoading(false);
      return () => { cancelled = true; };
    }
    setHistoryDetailLoading(true);
    Promise.all(([GOLD, SILVER] as Side[]).map(async (side): Promise<ChainPositionView | null> => {
      try {
        const [positionValue, quoteValue] = await Promise.all([
          readContract("get_position", [selectedHistoryMarketId, walletAddress, side]),
          readContract("get_claim_quote", [selectedHistoryMarketId, walletAddress, side]),
        ]);
        const position = record<ContractPosition>(positionValue);
        if (!position.exists) return null;
        return {
          position,
          market: selectedHistoryMarket,
          quote: record<ClaimQuote>(quoteValue),
        };
      } catch {
        return null;
      }
    })).then((views: Array<ChainPositionView | null>) => {
      if (!cancelled) setSelectedHistoryPositionViews(views.filter((view): view is ChainPositionView => Boolean(view)));
    }).finally(() => {
      if (!cancelled) setHistoryDetailLoading(false);
    });
    return () => { cancelled = true; };
  }, [mode, selectedHistoryMarket, selectedHistoryMarketId, walletAddress]);

  async function handleLoadMorePositions() {
    if (!walletAddress || mode !== "contract" || !positionsHaveMore || isRefreshing) return;
    setIsRefreshing(true);
    try {
      const pageValue = await readContract("get_user_positions", [walletAddress, positionNextOffset, POSITION_PAGE_SIZE]);
      const page = record<ContractPositionPage>(pageValue);
      const rawPositions = rawList(pageValue, "positions").map((value) => record<ContractPosition>(value));
      const enriched = await enrichPositions(rawPositions, walletAddress);
      setContractPositions((current) => {
        const seen = new Set(current.map((view) => `${view.position.market_id}-${view.position.side}`));
        return [...current, ...enriched.filter((view) => !seen.has(`${view.position.market_id}-${view.position.side}`))];
      });
      const nextOffset = toBigInt(page.next_offset) ?? positionNextOffset + BigInt(rawPositions.length);
      setPositionNextOffset(nextOffset);
      setPositionsHaveMore(Boolean(page.has_more));
    } catch (error) {
      setContractReadError(error instanceof Error ? error.message : "More positions are temporarily unavailable.");
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleLoadMoreHistory() {
    if (!historyHasMore || historyReadState === "loading") return;
    await loadHistoryPage(historyNextOffset, true);
  }

  function clearError() {
    setErrorMessage("");
    setContractReadError("");
  }

  function startLocalReplay() {
    clearError();
    setWrongNetwork(false);
    setMode("local");
    setWalletAddress("local-replay");
    setLocalBalance((value) => value ?? 1_000n);
    setTxState("IDLE");
    setStatusMessage("Local replay started. These positions never leave this browser.");
  }

  async function handleConnect() {
    clearError();
    if (!hasDeployment()) {
      startLocalReplay();
      return;
    }
    if (!hasWalletProvider()) {
      setErrorMessage("Install MetaMask or choose the local replay.");
      return;
    }
    try {
      await assertWalletNetwork();
      const address = await connectWallet();
      await assertWalletNetwork();
      setWalletAddress(address);
      setMode("contract");
      setWrongNetwork(false);
      setTxState("IDLE");
      setStatusMessage(`Connected to ${shortAddress(address)} on ${getConfiguredChain().name}.`);
    } catch (error) {
      if (error instanceof WrongNetworkError) setWrongNetwork(true);
      setErrorMessage(error instanceof Error ? error.message : "Wallet connection failed.");
    }
  }

  async function handleSwitchNetwork() {
    clearError();
    try {
      await switchToConfiguredNetwork();
      setWrongNetwork(false);
      setStatusMessage(`Wallet switched to ${getConfiguredChain().name}.`);
      await syncWallet();
    } catch (error) {
      setWrongNetwork(true);
      setErrorMessage(error instanceof Error ? error.message : "Network switch was cancelled.");
    }
  }

  async function runWrite(functionName: string, args: unknown[], label: string): Promise<boolean> {
    if (txBusy) return false;
    clearError();
    setTxLabel(label);
    setTxHash("");
    setTxState("SUBMITTED");
    setStatusMessage(`${label} submitted. Waiting for GenLayer protocol finality.`);
    try {
      const hash = await writeContract(functionName, args);
      setTxHash(hash);
      await waitForFinalizedTransaction(hash, (progress) => {
        setTxState(progress);
        if (progress === "PROVISIONAL") setStatusMessage(`${label} accepted provisionally. Waiting for protocol finality.`);
      });
      setTxState("FINALIZED");
      setStatusMessage(`${label} finalized successfully. State refreshed from the contract.`);
      await refreshContract();
      return true;
    } catch (error) {
      setTxState("FAILED");
      setErrorMessage(`${label}: ${error instanceof Error ? error.message : "transaction failed"}`);
      setStatusMessage(`${label} failed. No state change was assumed.`);
      return false;
    }
  }

  async function handleClaimCredits() {
    if (mode === "contract") {
      await runWrite("claim_demo_credits", [], "Demo credit request");
      return;
    }
    startLocalReplay();
  }

  async function handlePlacePosition() {
    if (!canPlacePosition) return;
    if (mode === "contract") {
      await runWrite("place_position", [activeMarketId, selectedSide, stakeValue], "Position submission");
      return;
    }
    if (localBalance !== null && localBalance < stakeValue) {
      setErrorMessage("Your local replay balance is below this stake.");
      return;
    }
    setLocalBalance((value) => (value ?? 1_000n) - stakeValue);
    setLocalPools((value) => ({ ...value, [selectedSide]: value[selectedSide] + stakeValue }));
    setLocalPositions((value) => [
      {
        id: `${activeMarketId}-${selectedSide}-${Date.now()}`,
        marketId: activeMarketId,
        side: selectedSide,
        stake: stakeValue,
        status: "LOCAL_REPLAY",
        payout: null,
        enteredAt: new Date(referenceNow).toISOString(),
      },
      ...value,
    ]);
    setTxHash("");
    setTxState("IDLE");
    setStatusMessage(`${selectedSide} local replay position recorded for ${formatCredits(stakeValue)} credits.`);
  }

  async function handleOpenNextMarket() {
    if (!contractCanOpenNext || wrongNetwork) return;
    await runWrite("open_next_market", [], "Next market opening");
  }

  async function handleSettlement(marketIdToSettle: string) {
    const view = contractPositions.find((item) => item.position.market_id === marketIdToSettle);
    const market = view?.market
      ?? historyMarkets.find((item) => item.market_id === marketIdToSettle)
      ?? (contractMarket?.market_id === marketIdToSettle ? contractMarket : null);
    if (!market || !isAfter(market.end_at, referenceNow) || isAfter(market.settlement_deadline, referenceNow)) return;
    if (mode === "contract") await runWrite("request_settlement", [marketIdToSettle], "Settlement request");
  }

  async function handleRefund(marketIdToRefund: string) {
    const view = contractPositions.find((item) => item.position.market_id === marketIdToRefund);
    const market = view?.market
      ?? historyMarkets.find((item) => item.market_id === marketIdToRefund)
      ?? (contractMarket?.market_id === marketIdToRefund ? contractMarket : null);
    if (!market || !isAfter(market.settlement_deadline, referenceNow)) return;
    if (mode === "contract") await runWrite("refund_after_deadline", [marketIdToRefund], "Deadline refund");
  }

  async function handleClaim(view: ChainPositionView) {
    if (!view.position.market_id || !view.position.side || view.quote?.claimed || view.quote?.finality_status !== "FINALIZED") return;
    await runWrite("claim_position", [view.position.market_id, view.position.side], "Payout claim");
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
    ? hasDeployment() ? "Connect wallet" : "Start local replay"
    : txBusy
      ? txState === "PROVISIONAL" ? "Awaiting finality…" : "Submitting…"
      : mode === "contract" && !contractEntryMarket && contractCanOpenNext
        ? "Open next market"
        : mode === "contract" && !contractEntryMarket
          ? contractMarket?.status === "LIVE" ? "Entry closed" : "Market unavailable"
          : walletBalance === null
            ? "Request 1,000 demo credits"
            : `Place ${selectedSide} position`;
  const txLink = explorerLink(txHash);
  const errorText = errorMessage || contractReadError;
  const loadedPositionCount = contractAccount?.position_count ?? contractPositions.length;
  const usesXausSource = protocolConfig.source_mode === "XAUS_INDICATIVE_HISTORICAL_REPLAY";
  const settlementSourceLabel = usesXausSource
    ? "XAUS indicative historical replay"
    : mode === "local" || !hasDeployment()
      ? "synthetic demo"
      : "configured source";
  const settlementDetailSubtitle = usesXausSource
    ? "Display-only synthetic example; the deployed XAUS source is fetched independently after expiry."
    : "Illustrative synthetic record — not live market evidence.";

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
            <button
              className="wallet-button connected"
              onClick={() => {
                setWalletAddress(null);
                setMode("idle");
                setContractAccount(null);
                setContractPositions([]);
                setStatusMessage("Wallet disconnected. Contract reads remain available.");
              }}
              aria-label={mode === "local" ? "Exit local replay" : `Disconnect wallet ${shortAddress(walletAddress)}`}
              title={mode === "local" ? "Exit local replay" : "Disconnect wallet"}
            >
              <WalletCards size={15} strokeWidth={1.8} />
              {mode === "local" ? "Local replay" : shortAddress(walletAddress)}
              <ChevronDown size={14} aria-hidden="true" />
            </button>
          ) : (
            <button className="wallet-button" onClick={hasDeployment() ? handleConnect : startLocalReplay}>
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
          <div className="truth-line"><Database size={13} />Settlement source: {settlementSourceLabel}</div>
          {usesXausSource && protocolConfig.source_terms_url ? <a className="truth-line" href={protocolConfig.source_terms_url} target="_blank" rel="noreferrer">XAUS terms: indicative / non-executable ↗</a> : null}
          <div className="truth-line"><LockKeyhole size={13} />2% fee frozen before entry</div>
        </div>
      </section>

      {errorText && (
        <div className="error-strip" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{errorText}</span>
          {wrongNetwork ? (
            <button onClick={handleSwitchNetwork}>Switch network</button>
          ) : (
            <button onClick={() => { clearError(); refreshContract().catch(() => undefined); }} aria-label="Retry contract read"><RefreshCw size={14} /></button>
          )}
        </div>
      )}
      <div className="sr-only" aria-live="polite" aria-atomic="true">{statusMessage}</div>

      <section className="interval-bar" aria-label="Interval status">
        <div className="interval-main">
          <div className="section-label">CURRENT INTERVAL</div>
          <div className="interval-time"><strong>{formatUtc(intervalStart)}</strong><span>→</span><strong>{formatUtc(intervalEnd)}</strong></div>
          <span className="utc-date">{formatDateUtc(intervalStart)}</span>
        </div>
        <div className="interval-state"><span className="live-indicator" /><span>{statusLabel(displayStatus)}</span><span className="provisional-tag">PROVISIONAL LEADER</span><strong className={provisionalLeader === GOLD ? "gold-text" : "silver-text"}>{provisionalLeader}</strong></div>
        <div className="interval-countdown">
          <Clock3 size={15} aria-hidden="true" />
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
              <div className="chart-meta"><span className="synthetic-tag">SYNTHETIC REPLAY</span><span className="refresh-readout"><span className="status-dot warm" />illustrative only</span></div>
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
              <div className="reading-callout"><span className="callout-kicker">INTERVAL CLOSES</span><strong>{formatUtc(intervalEnd)}</strong><span>Outcome remains provisional until the frozen evidence record is verified and protocol-finalized.</span></div>
            </div>
          </section>
        </div>

        <aside className="panel entry-panel" aria-labelledby="entry-heading">
          <h2 id="entry-heading" className="sr-only">Enter a MetalSwap prediction position</h2>
          <div className="entry-topline"><span className="section-label">{entryHeadingLabel}</span><span className={`entry-status ${entryStatusLabel !== "OPEN" ? "waiting" : ""}`}><span className="status-dot" /> {entryStatusLabel}</span></div>
          <div className="entry-date"><strong>{formatDateUtc(dateFrom(entryContextMarket?.start_at) ?? activeStart)}</strong><span>{formatUtc(dateFrom(entryContextMarket?.start_at) ?? activeStart)} → {formatUtc(dateFrom(entryContextMarket?.end_at) ?? activeEnd)}</span></div>
          <div className="entry-countdown"><span>{entryIsOpen ? "ENTRY CLOSES IN" : "MARKET STATE"}</span><strong>{entryIsOpen ? entryCountdown.label : statusLabel(contractMarket?.status ?? (mode === "local" ? "UPCOMING" : "CONNECT_TO_ENTER"))}</strong><small>{mode === "contract" ? "Contract state is read from GenLayer" : mode === "local" ? "Quarter-hour lock · UTC" : "Start a replay or connect to enter"}</small></div>

          {hasDeployment() && mode === "idle" ? (
            <div className="entry-help"><CircleHelp size={14} /><span>Connect a wallet to place a contract position, or <button className="inline-action" onClick={startLocalReplay}>try a local replay</button> with clearly synthetic credits.</span></div>
          ) : null}
          {mode === "contract" && !contractEntryMarket ? (
            <div className="entry-help"><CircleHelp size={14} /><span>{contractMarket?.status === "LIVE" ? "This market is already live; entries are locked until the next market opens." : walletIsMarketOperator ? "Operator control: open the next market only after this interval is complete." : "Market opening is operator-controlled. Historical markets remain readable and claimable."}</span></div>
          ) : null}

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
            <div className="pool-bar"><span className="pool-gold-fill" style={{ width: `${totalPool > 0n ? `${Number((pools.GOLD * 10_000n) / totalPool) / 100}%` : "50%"}` }} /><span className="pool-silver-fill" style={{ width: `${totalPool > 0n ? `${Number((pools.SILVER * 10_000n) / totalPool) / 100}%` : "50%"}` }} /></div>
            <div><span>SILVER POOL</span><strong>{poolStateKnown ? formatCredits(pools.SILVER) : "—"}</strong></div>
          </div>

          <div className="stake-block">
            <div className="stake-heading"><span>STAKE AMOUNT</span><span>DEMO CREDITS</span></div>
            <div className={`stake-input-wrap ${stakeError ? "invalid" : ""}`}>
              <input
                aria-label="Stake amount in demo credits"
                aria-describedby="stake-hint stake-error"
                aria-invalid={Boolean(stakeError)}
                inputMode="numeric"
                pattern="[0-9]*"
                type="text"
                minLength={1}
                maxLength={78}
                value={stakeAmount}
                onChange={(event) => setStakeAmount(event.target.value)}
              />
              <span>credits</span>
            </div>
            <p id="stake-hint" className="field-hint">Whole-number demo credits only.</p>
            {stakeError ? <p id="stake-error" className="field-error" role="status">{stakeError}</p> : null}
            <div className="quick-stakes" aria-label="Quick stake amounts">{[10, 25, 50, 100].map((amount) => <button key={amount} className={String(amount) === stakeAmount ? "active" : ""} onClick={() => setStakeAmount(String(amount))} aria-pressed={String(amount) === stakeAmount}>{amount}</button>)}</div>
          </div>

          <div className="estimate-row"><div><span>ESTIMATED PAYOUT</span><strong>{formatCredits(estimatedPayout)} credits</strong></div><span className="variable-label">variable until lock</span></div>
          <div className="payout-note">{opposingPool > 0n ? `2% fee applied to a two-sided pool · your share is proportional to your ${selectedSide} stake.` : "One-sided pool → your stake refunds without a fee if no opposing side funds."}</div>

          {!hasActiveSession ? (
            <button className="primary-action" onClick={hasDeployment() ? handleConnect : startLocalReplay}><WalletCards size={17} />{primaryLabel}<ArrowUpRight size={16} /></button>
          ) : mode === "contract" && !contractEntryMarket ? (
            <button className="primary-action" onClick={handleOpenNextMarket} disabled={!contractCanOpenNext || txBusy || wrongNetwork}><RefreshCw size={17} />{primaryLabel}<ArrowUpRight size={16} /></button>
          ) : walletBalance === null ? (
            <button className="primary-action" onClick={handleClaimCredits} disabled={txBusy || wrongNetwork}><Database size={17} />{primaryLabel}<ArrowUpRight size={16} /></button>
          ) : (
            <button className="primary-action" onClick={handlePlacePosition} disabled={!canPlacePosition}><ArrowUpRight size={17} />{primaryLabel}<span className="action-key">↵</span></button>
          )}
          <p className="action-disclosure"><ShieldCheck size={13} /> Demo credits only. No leverage, liquidation, custody, or physical metal ownership.</p>
        </aside>
      </section>

      <section className="lower-grid">
        <section className="panel positions-panel">
          <div className="panel-heading compact-heading"><div><h2>My positions</h2><p>Wallet-linked entries and claim availability.</p></div><span className="position-count">{formatCredits(loadedPositionCount)} total</span></div>
          {mode === "contract" && isRefreshing && contractPositions.length === 0 ? (
            <div className="empty-state"><div className="empty-icon"><RefreshCw size={18} className="spin" /></div><div><strong>Reading on-chain positions…</strong><span>Loading wallet-linked positions and claim status from GenLayer.</span></div></div>
          ) : localPositions.length === 0 && contractPositions.length === 0 ? (
            <div className="empty-state"><div className="empty-icon"><WalletCards size={18} /></div><div><strong>No positions yet</strong><span>{mode === "contract" ? "This wallet has no indexed on-chain positions yet." : "Choose GOLD or SILVER above to commit a prediction position for the upcoming interval."}</span></div></div>
          ) : (
            <div className="position-list">
              {localPositions.map((position) => <div className="position-row" key={position.id}><div className={`position-token ${position.side.toLowerCase()}`}><span className={`metal-swatch ${position.side === GOLD ? "gold-swatch" : "silver-swatch"}`} />{position.side}</div><div><strong>{formatCredits(position.stake)} credits</strong><span>Local replay · not on-chain</span></div><div className="position-state"><span className="state-dot" />LOCAL</div><span className="text-action disabled-action">Replay only</span></div>)}
              {contractPositions.map((view) => {
                const position = view.position;
                const market = view.market;
                const quote = view.quote;
                const marketIdToUse = position.market_id ?? "";
                const final = quote?.finality_status === "FINALIZED";
                const claimable = Boolean(final && quote?.exists && !quote.claimed && quote.payout !== undefined);
                const deadlineReached = Boolean(market && isAfter(market.settlement_deadline, referenceNow));
                const settlementReady = Boolean(market && ["AWAITING_SETTLEMENT", "PENDING_EVIDENCE"].includes(market.status ?? "") && isAfter(market.end_at, referenceNow) && !deadlineReached);
                const refundReady = Boolean(market && !market.outcome && deadlineReached);
                const state = quote?.claimed ? "CLAIMED" : claimable ? "CLAIMABLE" : market?.status ? statusLabel(market.status) : "READING";
                return <div className="position-row" key={`${position.market_id}-${position.side}`}>
                  <div className={`position-token ${position.side?.toLowerCase() ?? "contract"}`}><span className={`metal-swatch ${position.side === GOLD ? "gold-swatch" : "silver-swatch"}`} />{position.side ?? "POSITION"}</div>
                  <div><strong>{formatCredits(position.stake)} credits</strong><span>{marketIdToUse || "Market unavailable"} · {market ? statusLabel(market.status) : "refreshing"}</span></div>
                  <div className="position-state"><span className={`state-dot ${final ? "cyan" : ""}`} />{state}</div>
                  {settlementReady ? <button className="text-action" onClick={() => handleSettlement(marketIdToUse)} disabled={txBusy}>Settle<ArrowUpRight size={13} /></button>
                    : refundReady ? <button className="text-action" onClick={() => handleRefund(marketIdToUse)} disabled={txBusy}>Refund<ArrowUpRight size={13} /></button>
                      : claimable ? <button className="text-action" onClick={() => handleClaim(view)} disabled={txBusy}>Claim {formatCredits(quote?.payout)}<ArrowUpRight size={13} /></button>
                        : <span className="text-action disabled-action">{quote?.claimed ? "Claimed" : final ? "No payout" : "Awaiting finality"}</span>}
                </div>;
              })}
              {contractAccount && toSafeNumber(contractAccount.position_count) > contractPositions.length ? <div className="position-row contract-summary"><div className="position-token contract"><LockKeyhole size={14} />CHAIN</div><div><strong>{formatCredits(contractAccount.position_count)} contract positions</strong><span>{formatCredits(contractAccount.total_staked)} credits staked</span></div><div className="position-state"><span className="state-dot cyan" />PARTIAL READ</div><button className="text-action" onClick={refreshContract} disabled={isRefreshing}>{isRefreshing ? "Reading…" : "Refresh"}<RefreshCw size={13} /></button></div> : null}
              {positionsHaveMore ? <div className="history-pagination"><button className="secondary-action" onClick={handleLoadMorePositions} disabled={isRefreshing}>{isRefreshing ? "Reading…" : "Load older positions"}<RefreshCw size={13} /></button></div> : null}
            </div>
          )}
          {txHash && <div className="tx-notice"><span className={`state-dot ${txState === "FINALIZED" ? "cyan" : ""}`} /><span>{txLabel || "Transaction"} · {txState === "PROVISIONAL" ? "accepted provisionally; awaiting protocol finality" : txState === "FINALIZED" ? "finalized" : txState === "FAILED" ? "failed" : "processing"}</span>{txLink ? <a href={txLink} target="_blank" rel="noreferrer">View receipt <ExternalLink size={12} /></a> : <button onClick={() => copyText(txHash)}>{copied ? "Copied" : "Copy hash"} {copied ? <Check size={12} /> : <Copy size={12} />}</button>}</div>}
        </section>

        <section className="panel history-panel">
          <div className="panel-heading compact-heading"><div><h2>Settlement history</h2><p>Paginated on-chain markets and protocol finality.</p></div><span className="history-filter">{historyReadState === "loading" ? "READING…" : `${historyMarkets.length} MARKETS`}</span></div>
          {historyReadState === "loading" && historyMarkets.length === 0 ? (
            <div className="history-empty"><div className="history-orbit"><RefreshCw size={18} className="spin" /></div><strong>Reading market history…</strong><span>Fetching bounded pages from the MetalSwap contract.</span></div>
          ) : historyReadState === "unavailable" && historyMarkets.length === 0 ? (
            <div className="history-empty"><div className="history-orbit"><AlertTriangle size={18} /></div><strong>History unavailable</strong><span>{historyReadError || "The contract history read failed."}</span><button className="secondary-action" onClick={() => loadHistoryPage(0n, false)}><RefreshCw size={13} />Retry</button></div>
          ) : historyMarkets.length === 0 ? (
            <div className="history-empty"><div className="history-orbit"><Database size={18} /></div><strong>No markets indexed yet</strong><span>The operator has not opened a market on this deployment. The chart above is synthetic and is not trade history.</span></div>
          ) : (
            <>
              <div className="history-market-list" aria-label="On-chain market history">
                {historyMarkets.map((market) => {
                  const finalized = market.finality_status === "FINALIZED";
                  return <button
                    type="button"
                    className={`history-market-row ${selectedHistoryMarketId === market.market_id ? "selected" : ""}`}
                    key={market.market_id}
                    onClick={() => setSelectedHistoryMarketId(market.market_id ?? "")}
                    aria-pressed={selectedHistoryMarketId === market.market_id}
                  >
                    <span><strong>{market.market_id}</strong><small>{formatUtc(dateFrom(market.start_at))} → {formatUtc(dateFrom(market.end_at))}</small></span>
                    <span className="history-market-outcome">{market.outcome || statusLabel(market.status)}<small>{finalized ? "FINALIZED" : market.finality_status || "PENDING"}</small></span>
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </button>;
                })}
              </div>
              {selectedHistoryMarket ? (
                <div className="history-detail" aria-live="polite">
                  <div className="history-detail-heading"><div><span className="section-label">SELECTED MARKET</span><strong>{selectedHistoryMarket.market_id}</strong></div><span className={`history-state ${selectedHistoryMarket.finality_status === "FINALIZED" ? "finalized" : ""}`}>{statusLabel(selectedHistoryMarket.status)}</span></div>
                  <div className="history-detail-grid"><span><small>OUTCOME</small><strong>{selectedHistoryMarket.outcome || "Not settled"}</strong></span><span><small>POOL</small><strong>{formatCredits(selectedHistoryMarket.total_staked)} credits</strong></span><span><small>FINALITY</small><strong>{selectedHistoryMarket.finality_status || "PENDING"}</strong></span></div>
                  {selectedHistoryMarket.evidence_url ? <a className="history-evidence-link" href={selectedHistoryMarket.evidence_url} target="_blank" rel="noreferrer">Open frozen evidence <ExternalLink size={12} /></a> : null}
                  {historyDetailLoading ? <div className="history-detail-note"><RefreshCw size={13} className="spin" />Reading this wallet’s position…</div> : walletAddress && selectedHistoryPositionViews.length > 0 ? (
                    <div className="history-position-list">
                      {selectedHistoryPositionViews.map((view) => {
                        const final = view.quote?.finality_status === "FINALIZED";
                        const claimable = Boolean(final && view.quote?.exists && !view.quote.claimed && view.quote.payout !== undefined);
                        return <div className="history-position-row" key={`${view.position.market_id}-${view.position.side}`}><span><strong>{view.position.side}</strong><small>{formatCredits(view.position.stake)} credits staked</small></span><span>{view.quote?.claimed ? "CLAIMED" : final ? `${formatCredits(view.quote?.payout)} claimable` : "Awaiting finality"}</span>{claimable ? <button className="text-action" onClick={() => handleClaim(view)} disabled={txBusy}>Claim<ArrowUpRight size={13} /></button> : null}</div>;
                      })}
                    </div>
                  ) : <div className="history-detail-note">{walletAddress ? "This wallet has no position in the selected market." : "Connect a wallet to inspect and claim a historical position."}</div>}
                </div>
              ) : null}
              {historyHasMore ? <div className="history-pagination"><button className="secondary-action" onClick={handleLoadMoreHistory} disabled={historyReadState === "loading"}>{historyReadState === "loading" ? "Reading…" : "Load older markets"}<RefreshCw size={13} /></button></div> : null}
            </>
          )}
        </section>
      </section>

      <section className="protocol-strip">
        <div className="protocol-title"><span className="protocol-icon"><ShieldCheck size={16} /></span><div><strong>Evidence & finality</strong><span>Every outcome follows a separately readable protocol path.</span></div></div>
        <div className="protocol-steps"><span><b>01</b>Expiry</span><ArrowDownRight size={14} /><span><b>02</b>Evidence agreement</span><ArrowDownRight size={14} /><span><b>03</b>Protocol finality</span><ArrowDownRight size={14} /><span><b>04</b>Claim / refund</span></div>
        <button className="details-link" onClick={() => document.getElementById("settlement-detail")?.scrollIntoView({ behavior: "smooth" })}>Read settlement detail <ArrowUpRight size={14} /></button>
      </section>

      <section id="settlement-detail" className="settlement-detail">
        <div className="detail-heading"><div><h2>What gets verified at settlement</h2><p>{settlementDetailSubtitle}</p></div><div className="detail-heading-actions"><a className="details-link" href="/comparison/metalswap-synthetic-2026-09-14-07-30-00z">Open public comparison proof <ExternalLink size={13} /></a><span className="synthetic-tag">SYNTHETIC REPLAY · NOT LIVE</span></div></div>
        <div className="detail-layout">
          <div className="evidence-table-wrap">
            <table className="evidence-table"><thead><tr><th>BENCHMARK</th><th>OPEN</th><th>CLOSE</th><th>RETURN</th></tr></thead><tbody><tr><td><span className="metal-swatch gold-swatch" />GOLD <small>XAU / USD</small></td><td>{formatPrice(replayEvidence.goldOpen)}</td><td>{formatPrice(replayEvidence.goldClose)}</td><td className="gold-text">{formatPercent(replayEvidence.goldReturn)}</td></tr><tr><td><span className="metal-swatch silver-swatch" />SILVER <small>XAG / USD</small></td><td>{formatPrice(replayEvidence.silverOpen)}</td><td>{formatPrice(replayEvidence.silverClose)}</td><td className="silver-text">{formatPercent(replayEvidence.silverReturn)}</td></tr></tbody></table>
            <div className="table-footnote"><Clock3 size={13} /> Boundary observations are read after expiry. Values shown here are illustrative synthetic data, not settlement evidence.</div>
          </div>
          <div className="outcome-card"><span className="section-label">ILLUSTRATIVE OUTCOME</span><div className="outcome-name silver-text">SILVER <span>OUTPERFORMS</span></div><p>Validators compare the frozen evidence fields. Deterministic code compares:</p><code>silver_close × gold_open<br /><strong>&gt; gold_close × silver_open</strong></code><div className="outcome-note"><ShieldCheck size={14} /><span>Finality status: <strong>example only</strong><br />Claims remain gated until protocol finality.</span></div></div>
        </div>
        <div className="rule-grid"><div><span>FROZEN SOURCE ID</span><strong>{protocolConfig.source_id}</strong></div><div><span>RULE VERSION</span><strong>{protocolConfig.rule_version}</strong></div><div><span>OBSERVATION WINDOW</span><strong>exact boundary · ≤{toSafeNumber(protocolConfig.max_gap_seconds)}s gap</strong></div><div><span>CONFLICT PATH</span><strong>PENDING EVIDENCE → fee-free refund</strong></div></div>
      </section>

      <footer className="footer-bar"><span>MetalSwap · GenLayer testnet prototype</span><span className="footer-links"><a href="https://docs.genlayer.com/" target="_blank" rel="noreferrer">GenLayer docs <ExternalLink size={12} /></a><a href="https://xaus.com/api/" target="_blank" rel="noreferrer">Source feasibility <ExternalLink size={12} /></a><span className="footer-rpc">{GENLAYER_RPC_URL || "RPC not configured"}</span></span></footer>
    </main>
  );
}

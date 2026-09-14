/**
 * Deploy MetalSwap's finality gate and market contract, wire them once, freeze
 * the evidence origin, open the next UTC quarter-hour, and record only the
 * observed receipts/readback.
 *
 * Required before running:
 *   $env:METALSWAP_SOURCE_BASE_URL = "https://<host>/evidence/"
 *   genlayer network set studionet   # or another configured testnet
 *   genlayer deploy
 */

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import {
  TransactionStatus,
  executionResultNumberToName,
  transactionsStatusNumberToName,
} from "genlayer-js/types";
import type {
  CalldataEncodable,
  DecodedDeployData,
  GenLayerChain,
  GenLayerClient,
  GenLayerTransaction,
  TransactionHash,
} from "genlayer-js/types";

const GATE_SOURCE = "contracts/settlement_gate.py";
const MARKET_SOURCE = "contracts/metalswap.py";
const XAUS_SOURCE_BASE_URL = "https://xaus.com/api/v1/intraday";
const XAUS_EVIDENCE_URL = "https://xaus.com/api/v1/intraday?hours=48";
const ADDRESS_PATTERN = /^0x[a-fA-F0-9]{40}$/;

type Loose = Record<string, any>;

function env(name: string, fallback = ""): string {
  const value = process.env[name];
  return value === undefined || value.trim() === "" ? fallback : value.trim();
}

function address(value: string, label: string): string {
  if (!ADDRESS_PATTERN.test(value)) throw new Error(`${label} is not a valid address: ${value}`);
  return value.toLowerCase();
}

function preparedQuarterHour(now = new Date()): string {
  const quarterMs = 15 * 60 * 1_000;
  const earliestMs = now.getTime() + 10 * 60 * 1_000;
  const startMs = Math.ceil(earliestMs / quarterMs) * quarterMs;
  return new Date(startMs).toISOString().replace(".000Z", "Z");
}

function receiptStatus(receipt: GenLayerTransaction): string {
  const raw = receipt as unknown as Loose;
  if (typeof raw.statusName === "string") return raw.statusName.toUpperCase();
  if (typeof raw.status_name === "string") return raw.status_name.toUpperCase();
  if (typeof raw.status === "number" || typeof raw.status === "string") {
    return String((transactionsStatusNumberToName as Record<string, string>)[String(raw.status)] ?? raw.status).toUpperCase();
  }
  return "UNKNOWN";
}

function executionStatus(receipt: GenLayerTransaction): string {
  const raw = receipt as unknown as Loose;
  const direct = raw.txExecutionResultName ?? raw.tx_execution_result_name;
  if (typeof direct === "string") return direct.toUpperCase();
  const numeric = raw.txExecutionResult ?? raw.tx_execution_result;
  if (typeof numeric === "number" || typeof numeric === "string") {
    return String((executionResultNumberToName as Record<string, string>)[String(numeric)] ?? numeric).toUpperCase();
  }
  const leader = raw.consensus_data?.leader_receipt?.[0];
  return typeof leader?.execution_result === "string" ? leader.execution_result.toUpperCase() : "UNKNOWN";
}

function assertSucceeded(label: string, receipt: GenLayerTransaction): GenLayerTransaction {
  const consensus = receiptStatus(receipt);
  const execution = executionStatus(receipt);
  if (consensus !== "FINALIZED" || !["SUCCESS", "FINISHED_WITH_RETURN"].includes(execution)) {
    throw new Error(`${label} failed: consensus=${consensus}, execution=${execution}. Receipt=${JSON.stringify(receipt)}`);
  }
  return receipt;
}

class Deployer {
  private readonly retries = Number(env("METALSWAP_WAIT_RETRIES", "200"));
  private readonly completed: Array<{ label: string; hash: string; consensus: string; execution: string }> = [];

  constructor(private readonly client: GenLayerClient<GenLayerChain>) {}

  private async wait(hash: TransactionHash): Promise<GenLayerTransaction> {
    return this.client.waitForTransactionReceipt({
      hash,
      status: TransactionStatus.FINALIZED,
      interval: 5_000,
      retries: this.retries,
    });
  }

  private record(label: string, hash: TransactionHash, receipt: GenLayerTransaction) {
    this.completed.push({ label, hash: String(hash), consensus: receiptStatus(receipt), execution: executionStatus(receipt) });
  }

  async deploy(label: string, source: string): Promise<`0x${string}`> {
    console.log(`\n▸ ${label}: deploying ${source}`);
    const code = new Uint8Array(readFileSync(path.resolve(process.cwd(), source)));
    const hash = (await this.client.deployContract({ code, args: [] })) as TransactionHash;
    const receipt = assertSucceeded(label, await this.wait(hash));
    this.record(label, hash, receipt);
    const data = receipt.data as Loose | undefined;
    const decoded = receipt.txDataDecoded as DecodedDeployData | undefined;
    const deployed = data?.contract_address ?? decoded?.contractAddress;
    if (typeof deployed !== "string" || !ADDRESS_PATTERN.test(deployed)) {
      throw new Error(`${label} did not return a contract address.`);
    }
    console.log(`  ✓ ${deployed} (${hash}) · ${receiptStatus(receipt)}`);
    return deployed as `0x${string}`;
  }

  async write(label: string, contract: `0x${string}`, functionName: string, args: CalldataEncodable[]) {
    console.log(`▸ ${label}`);
    const hash = (await this.client.writeContract({ address: contract, functionName, args, value: 0n })) as TransactionHash;
    const receipt = assertSucceeded(label, await this.wait(hash));
    this.record(label, hash, receipt);
    console.log(`  ✓ ${hash} · ${receiptStatus(receipt)}`);
    return hash;
  }

  transactions() {
    return this.completed;
  }
}

export default async function main(client: GenLayerClient<GenLayerChain>) {
  const sourceBaseUrl = env("METALSWAP_SOURCE_BASE_URL");
  const isXausSource = sourceBaseUrl === XAUS_SOURCE_BASE_URL;
  if (!sourceBaseUrl.startsWith("https://") || (!sourceBaseUrl.endsWith("/") && !isXausSource)) {
    throw new Error("Set METALSWAP_SOURCE_BASE_URL to the exact hosted HTTPS evidence directory or https://xaus.com/api/v1/intraday.");
  }

  const deployer = new Deployer(client);
  const gateAddress = await deployer.deploy("1/6 SettlementGate", GATE_SOURCE);
  const marketAddress = await deployer.deploy("2/6 MetalSwap", MARKET_SOURCE);

  await deployer.write("3/6 Bind gate → market", gateAddress, "configure_market", [address(marketAddress, "MetalSwap address")]);
  await deployer.write("4/6 Bind market → gate", marketAddress, "configure_finality_gate", [address(gateAddress, "SettlementGate address")]);
  await deployer.write("5/6 Freeze evidence source", marketAddress, "configure_source_base_url", [sourceBaseUrl]);
  const startAt = preparedQuarterHour();
  const marketId = `market-${startAt}`;
  const evidenceUrl = isXausSource ? XAUS_EVIDENCE_URL : `${sourceBaseUrl}${marketId}.json`;
  const marketOpenHash = await deployer.write(
    "6/6 Open prepared future UTC quarter-hour",
    marketAddress,
    "open_market",
    [marketId, startAt, evidenceUrl],
  );

  const market = await client.readContract({ address: marketAddress, functionName: "get_current_market", args: [] });
  const config = await client.readContract({ address: marketAddress, functionName: "get_protocol_config", args: [] });
  const gate = await client.readContract({ address: gateAddress, functionName: "get_gate_status", args: [] });
  const network = (client.chain as GenLayerChain | undefined)?.name ?? "unknown-network";
  const outputPath = path.resolve(process.cwd(), "deploy/last-deployment.json");
  let previousSyntheticDeployment: Loose | undefined;
  try {
    const previous = JSON.parse(readFileSync(outputPath, "utf-8")) as Loose;
    if (previous?.demo) {
      previousSyntheticDeployment = {
        network: previous.network,
        deployedAt: previous.deployedAt,
        sourceRevision: previous.sourceRevision,
        metalSwapAddress: previous.metalSwapAddress,
        settlementGateAddress: previous.settlementGateAddress,
        demo: previous.demo,
      };
    }
  } catch {
    previousSyntheticDeployment = undefined;
  }
  const record = {
    network,
    deployedAt: new Date().toISOString(),
    sourceRevision: env("METALSWAP_SOURCE_REVISION", "unknown"),
    sourceMode: isXausSource ? "XAUS_INDICATIVE_HISTORICAL_REPLAY" : "SYNTHETIC_DEMO",
    sourceBaseUrl,
    settlementGateAddress: gateAddress,
    metalSwapAddress: marketAddress,
    marketOpenTransaction: String(marketOpenHash),
    deploymentTransactions: deployer.transactions(),
    readback: { market, config, gate },
    ...(previousSyntheticDeployment ? { previousSyntheticDeployment } : {}),
  };
  writeFileSync(outputPath, `${JSON.stringify(record, null, 2)}\n`, "utf-8");
  console.log(`\nMetalSwap deployed on ${network}. Observed state recorded at ${outputPath}`);
  console.log(`  NEXT_PUBLIC_METALSWAP_ADDRESS=${marketAddress}`);
  console.log(`  NEXT_PUBLIC_SETTLEMENT_GATE_ADDRESS=${gateAddress}`);
}

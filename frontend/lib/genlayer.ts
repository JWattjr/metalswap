"use client";

import { createClient } from "genlayer-js";
import { localnet, studionet, testnetAsimov, testnetBradbury } from "genlayer-js/chains";
import {
  ExecutionResult,
  TransactionStatus,
  transactionsStatusNumberToName,
} from "genlayer-js/types";
import type { GenLayerChain, GenLayerClient, GenLayerTransaction, TransactionHash } from "genlayer-js/types";

import {
  getConnectedAccount,
  getWalletChainId,
  switchWalletNetwork,
  type WalletNetworkParams,
} from "./wallet";

export const METALSWAP_ADDRESS = (process.env.NEXT_PUBLIC_METALSWAP_ADDRESS ?? "").trim();
export const SETTLEMENT_GATE_ADDRESS = (
  process.env.NEXT_PUBLIC_SETTLEMENT_GATE_ADDRESS
  ?? process.env.NEXT_PUBLIC_METALSWAP_GATE_ADDRESS
  ?? ""
).trim();
export const GENLAYER_RPC_URL = (process.env.NEXT_PUBLIC_GENLAYER_RPC_URL ?? "").trim();
export const NETWORK_NAME = (
  process.env.NEXT_PUBLIC_GENLAYER_NETWORK
  ?? process.env.NEXT_PUBLIC_GENLAYER_CHAIN_NAME
  ?? "GenLayer StudioNet"
).trim();

export type TransactionProgress = "SUBMITTED" | "PROVISIONAL" | "FINALIZED";

export class WrongNetworkError extends Error {
  readonly expectedChainId: number;
  readonly actualChainId: number | null;

  constructor(expectedChainId: number, actualChainId: number | null, networkName: string) {
    super(
      actualChainId === null
        ? `Wallet network could not be read. Switch to ${networkName} before writing.`
        : `Wallet is on chain ${actualChainId}; switch to ${networkName} (chain ${expectedChainId}) before writing.`,
    );
    this.name = "WrongNetworkError";
    this.expectedChainId = expectedChainId;
    this.actualChainId = actualChainId;
  }
}

function chainForEndpoint(endpoint: string): GenLayerChain {
  if (/127\.0\.0\.1|localhost/i.test(endpoint)) return localnet as GenLayerChain;
  if (/bradbury/i.test(endpoint)) return testnetBradbury as GenLayerChain;
  if (/asimov/i.test(endpoint)) return testnetAsimov as GenLayerChain;
  return studionet as GenLayerChain;
}

function chainForNetwork(network: string, endpoint: string): GenLayerChain {
  const normalized = network.toLowerCase().replace(/[-\s]/g, "_");
  if (normalized.includes("localnet") || /127\.0\.0\.1|localhost/i.test(endpoint)) return localnet as GenLayerChain;
  if (normalized.includes("bradbury")) return testnetBradbury as GenLayerChain;
  if (normalized.includes("asimov")) return testnetAsimov as GenLayerChain;
  if (normalized.includes("studio")) return studionet as GenLayerChain;
  return chainForEndpoint(endpoint);
}

export function getConfiguredChain(): GenLayerChain {
  return chainForNetwork(NETWORK_NAME, GENLAYER_RPC_URL);
}

export function getExpectedChainId(): number {
  return getConfiguredChain().id;
}

export function getExpectedChainIdHex(): string {
  return `0x${getExpectedChainId().toString(16)}`;
}

export function getConfiguredNetworkParams(): WalletNetworkParams {
  const chain = getConfiguredChain();
  return {
    chainId: `0x${chain.id.toString(16)}`,
    chainName: chain.name,
    rpcUrls: [...chain.rpcUrls.default.http],
    nativeCurrency: {
      name: chain.nativeCurrency.name,
      symbol: chain.nativeCurrency.symbol,
      decimals: chain.nativeCurrency.decimals,
    },
    ...(chain.blockExplorers?.default?.url ? { blockExplorerUrls: [chain.blockExplorers.default.url] } : {}),
  };
}

export function hasDeployment(): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(METALSWAP_ADDRESS) && /^0x[a-fA-F0-9]{40}$/.test(SETTLEMENT_GATE_ADDRESS);
}

export async function assertWalletNetwork(): Promise<void> {
  const actualChainId = await getWalletChainId();
  const expectedChainId = getExpectedChainId();
  if (actualChainId !== expectedChainId) {
    throw new WrongNetworkError(expectedChainId, actualChainId, getConfiguredChain().name);
  }
}

export async function switchToConfiguredNetwork(): Promise<void> {
  await switchWalletNetwork(getConfiguredNetworkParams());
  await assertWalletNetwork();
}

export async function createMetalSwapClient(): Promise<GenLayerClient<GenLayerChain>> {
  const account = await getConnectedAccount();
  const config: Record<string, unknown> = {
    chain: getConfiguredChain(),
    ...(GENLAYER_RPC_URL ? { endpoint: GENLAYER_RPC_URL } : {}),
  };
  if (account) config.account = account;
  if (typeof window !== "undefined" && window.ethereum) config.provider = window.ethereum;
  return createClient(config as never) as GenLayerClient<GenLayerChain>;
}

export function normalizeContractValue<T>(value: T): T {
  if (value instanceof Map) {
    return Object.fromEntries(Array.from(value.entries()).map(([key, nested]) => [String(key), normalizeContractValue(nested)])) as T;
  }
  if (Array.isArray(value)) return value.map((nested) => normalizeContractValue(nested)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, nested]) => [key, normalizeContractValue(nested)])) as T;
  }
  return value;
}

function contractAddress(value: string): `0x${string}` {
  return value as `0x${string}`;
}

export async function readContract(functionName: string, args: unknown[] = []): Promise<unknown> {
  if (!hasDeployment()) throw new Error("The MetalSwap contract addresses are not configured.");
  const client = await createMetalSwapClient();
  const value = await client.readContract({
    address: contractAddress(METALSWAP_ADDRESS),
    functionName,
    args: args as never,
  });
  return normalizeContractValue(value);
}

export async function readGateContract(functionName: string, args: unknown[] = []): Promise<unknown> {
  if (!/^0x[a-fA-F0-9]{40}$/.test(SETTLEMENT_GATE_ADDRESS)) {
    throw new Error("The SettlementGate contract address is not configured.");
  }
  const client = await createMetalSwapClient();
  const value = await client.readContract({
    address: contractAddress(SETTLEMENT_GATE_ADDRESS),
    functionName,
    args: args as never,
  });
  return normalizeContractValue(value);
}

function transactionHash(value: string): TransactionHash {
  if (!/^0x[0-9a-fA-F]{64}$/.test(value)) throw new Error("GenLayer returned an invalid transaction hash.");
  return value as TransactionHash;
}

function transactionStatusName(transaction: GenLayerTransaction): string {
  const raw = transaction as GenLayerTransaction & Record<string, unknown>;
  if (typeof raw.statusName === "string") return raw.statusName.toUpperCase();
  if (typeof raw.status === "number" || typeof raw.status === "string") {
    return String((transactionsStatusNumberToName as Record<string, string>)[String(raw.status)] ?? raw.status).toUpperCase();
  }
  return "UNKNOWN";
}

function executionStatusName(transaction: GenLayerTransaction): string {
  const raw = transaction as GenLayerTransaction & Record<string, unknown>;
  if (typeof raw.txExecutionResultName === "string") return raw.txExecutionResultName.toUpperCase();
  if (typeof raw.txExecutionResult === "number" || typeof raw.txExecutionResult === "string") {
    const names = { "0": ExecutionResult.NOT_VOTED, "1": ExecutionResult.FINISHED_WITH_RETURN, "2": ExecutionResult.FINISHED_WITH_ERROR };
    return String(names[String(raw.txExecutionResult) as keyof typeof names] ?? raw.txExecutionResult).toUpperCase();
  }
  const leader = raw.consensus_data?.leader_receipt?.[0] as Record<string, unknown> | undefined;
  return typeof leader?.execution_result === "string" ? leader.execution_result.toUpperCase() : "UNKNOWN";
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export async function writeContract(functionName: string, args: unknown[] = []): Promise<string> {
  if (!hasDeployment()) throw new Error("The MetalSwap contract addresses are not configured.");
  await assertWalletNetwork();
  const account = await getConnectedAccount();
  if (!account) throw new Error("Connect a wallet before submitting a transaction.");
  const client = await createMetalSwapClient();
  const hash = await client.writeContract({
    address: contractAddress(METALSWAP_ADDRESS),
    functionName,
    args: args as never,
    value: 0n,
  });
  return transactionHash(String(hash));
}

export async function waitForFinalizedTransaction(
  hash: string,
  onProgress?: (progress: TransactionProgress) => void,
): Promise<GenLayerTransaction> {
  const client = await createMetalSwapClient();
  const typedHash = transactionHash(hash);
  const maxPolls = 180;
  onProgress?.("SUBMITTED");

  for (let attempt = 0; attempt < maxPolls; attempt += 1) {
    const transaction = await client.getTransaction({ hash: typedHash });
    const status = transactionStatusName(transaction);
    if (["ACCEPTED", "READY_TO_FINALIZE", "UNDETERMINED", "APPEAL_REVEALING", "APPEAL_COMMITTING"].includes(status)) {
      onProgress?.("PROVISIONAL");
    }
    if (["CANCELED", "VALIDATORS_TIMEOUT", "LEADER_TIMEOUT"].includes(status)) {
      throw new Error(`Transaction ${status.toLowerCase().replaceAll("_", " ")}.`);
    }
    if (status === "FINALIZED") {
      const receipt = await client.waitForTransactionReceipt({
        hash: typedHash,
        status: TransactionStatus.FINALIZED,
        interval: 1_000,
        retries: 1,
      });
      const execution = executionStatusName(receipt);
      if (execution === ExecutionResult.FINISHED_WITH_ERROR) {
        throw new Error("GenLayer finalized the transaction, but contract execution failed.");
      }
      onProgress?.("FINALIZED");
      return receipt;
    }
    await delay(2_000);
  }
  throw new Error("Timed out waiting for GenLayer protocol finality. You can refresh and retry safely.");
}

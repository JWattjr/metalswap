"use client";

import { createClient } from "genlayer-js";
import { localnet, studionet, testnetAsimov, testnetBradbury } from "genlayer-js/chains";

import { getConnectedAccount } from "./wallet";
import type { GenLayerChain } from "genlayer-js/types";

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

export const METALSWAP_ABI = [
  { type: "function", name: "get_current_market", stateMutability: "view", inputs: [], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_protocol_config", stateMutability: "view", inputs: [], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_account", stateMutability: "view", inputs: [{ name: "owner", type: "address" }], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_user_positions", stateMutability: "view", inputs: [{ name: "owner", type: "address" }, { name: "offset", type: "uint256" }, { name: "limit", type: "uint256" }], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_market", stateMutability: "view", inputs: [{ name: "market_id", type: "string" }], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_position", stateMutability: "view", inputs: [{ name: "market_id", type: "string" }, { name: "owner", type: "address" }, { name: "side", type: "string" }], outputs: [{ type: "tuple" }] },
  { type: "function", name: "get_claim_quote", stateMutability: "view", inputs: [{ name: "market_id", type: "string" }, { name: "owner", type: "address" }, { name: "side", type: "string" }], outputs: [{ type: "tuple" }] },
  { type: "function", name: "claim_demo_credits", stateMutability: "nonpayable", inputs: [], outputs: [] },
  { type: "function", name: "place_position", stateMutability: "nonpayable", inputs: [{ name: "market_id", type: "string" }, { name: "side", type: "string" }, { name: "amount", type: "uint256" }], outputs: [] },
  { type: "function", name: "request_settlement", stateMutability: "nonpayable", inputs: [{ name: "market_id", type: "string" }], outputs: [] },
  { type: "function", name: "refund_after_deadline", stateMutability: "nonpayable", inputs: [{ name: "market_id", type: "string" }], outputs: [] },
  { type: "function", name: "claim_position", stateMutability: "nonpayable", inputs: [{ name: "market_id", type: "string" }, { name: "side", type: "string" }], outputs: [] },
] as const;

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

export function hasDeployment(): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(METALSWAP_ADDRESS);
}

export async function createMetalSwapClient() {
  const account = await getConnectedAccount();
  const config: Record<string, unknown> = {
    chain: chainForNetwork(NETWORK_NAME, GENLAYER_RPC_URL),
    ...(GENLAYER_RPC_URL ? { endpoint: GENLAYER_RPC_URL } : {}),
  };
  if (account) config.account = account;
  if (typeof window !== "undefined" && window.ethereum) config.provider = window.ethereum;
  return createClient(config as never);
}

export function normalizeContractValue<T>(value: T): T {
  if (typeof value === "bigint") return Number(value) as T;
  if (value instanceof Map) {
    return Object.fromEntries(Array.from(value.entries()).map(([key, nested]) => [String(key), normalizeContractValue(nested)])) as T;
  }
  if (Array.isArray(value)) return value.map((nested) => normalizeContractValue(nested)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, nested]) => [key, normalizeContractValue(nested)])) as T;
  }
  return value;
}

export async function readContract(functionName: string, args: unknown[] = []): Promise<unknown> {
  if (!hasDeployment()) throw new Error("The MetalSwap contract address is not configured.");
  const client = await createMetalSwapClient();
  const value = await (client as any).readContract({ address: METALSWAP_ADDRESS, abi: METALSWAP_ABI, functionName, args });
  return normalizeContractValue(value);
}

export async function writeContract(functionName: string, args: unknown[] = []): Promise<string> {
  if (!hasDeployment()) throw new Error("The MetalSwap contract address is not configured.");
  const client = await createMetalSwapClient();
  const hash = await (client as any).writeContract({ address: METALSWAP_ADDRESS, abi: METALSWAP_ABI, functionName, args, value: BigInt(0) });
  return String(hash);
}

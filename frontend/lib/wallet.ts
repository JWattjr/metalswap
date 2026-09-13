export interface EthereumProvider {
  isMetaMask?: boolean;
  providers?: EthereumProvider[];
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

const ADDRESS_PATTERN = /^0x[a-fA-F0-9]{40}$/;

function provider(): EthereumProvider | null {
  if (typeof window === "undefined") return null;
  const injected = window.ethereum;
  const providers = Array.isArray(injected?.providers) ? injected.providers : [];
  return providers.find((candidate) => candidate.isMetaMask) ?? injected ?? null;
}

export function hasWalletProvider(): boolean {
  return Boolean(provider());
}

export function isAddress(value: string): boolean {
  return ADDRESS_PATTERN.test(value);
}

export async function getConnectedAccount(): Promise<string | null> {
  const current = provider();
  if (!current) return null;
  const accounts = await current.request({ method: "eth_accounts" });
  const address = Array.isArray(accounts) ? String(accounts[0] ?? "") : "";
  return isAddress(address) ? address : null;
}

export async function connectWallet(): Promise<string> {
  const current = provider();
  if (!current) throw new Error("Install MetaMask or choose the local replay.");
  try {
    const accounts = await current.request({ method: "eth_requestAccounts" });
    const address = Array.isArray(accounts) ? String(accounts[0] ?? "") : "";
    if (!isAddress(address)) throw new Error("No wallet account was returned.");
    return address;
  } catch (error) {
    const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
    if (code === "4001") throw new Error("Wallet connection was cancelled.");
    throw error instanceof Error ? error : new Error("Wallet connection failed.");
  }
}

export function shortAddress(address: string): string {
  return address.length > 12 ? `${address.slice(0, 6)}…${address.slice(-4)}` : address;
}

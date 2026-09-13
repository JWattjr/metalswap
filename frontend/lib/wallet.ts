export interface EthereumProvider {
  isMetaMask?: boolean;
  providers?: EthereumProvider[];
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
}

export interface WalletNetworkParams {
  chainId: string;
  chainName: string;
  rpcUrls: string[];
  nativeCurrency: { name: string; symbol: string; decimals: number };
  blockExplorerUrls?: string[];
}

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

const ADDRESS_PATTERN = /^0x[a-fA-F0-9]{40}$/;

export function getWalletProvider(): EthereumProvider | null {
  if (typeof window === "undefined") return null;
  const injected = window.ethereum;
  const providers = Array.isArray(injected?.providers) ? injected.providers : [];
  return providers.find((candidate) => candidate.isMetaMask) ?? injected ?? null;
}

export function hasWalletProvider(): boolean {
  return Boolean(getWalletProvider());
}

export function isAddress(value: string): boolean {
  return ADDRESS_PATTERN.test(value);
}

export async function getConnectedAccount(): Promise<string | null> {
  const current = getWalletProvider();
  if (!current) return null;
  const accounts = await current.request({ method: "eth_accounts" });
  const address = Array.isArray(accounts) ? String(accounts[0] ?? "") : "";
  return isAddress(address) ? address : null;
}

export async function getWalletChainId(): Promise<number | null> {
  const current = getWalletProvider();
  if (!current) return null;
  const chainId = await current.request({ method: "eth_chainId" });
  if (typeof chainId !== "string" || !/^0x[0-9a-f]+$/i.test(chainId)) return null;
  const parsed = Number.parseInt(chainId.slice(2), 16);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function walletEventAccount(value: unknown): string | null {
  const accounts = Array.isArray(value) ? value : [];
  const address = String(accounts[0] ?? "");
  return isAddress(address) ? address : null;
}

export function subscribeToWalletEvents(
  handlers: { accountsChanged?: (...args: unknown[]) => void; chainChanged?: (...args: unknown[]) => void },
): () => void {
  const current = getWalletProvider();
  if (!current?.on) return () => undefined;
  if (handlers.accountsChanged) current.on("accountsChanged", handlers.accountsChanged);
  if (handlers.chainChanged) current.on("chainChanged", handlers.chainChanged);
  return () => {
    if (handlers.accountsChanged) current.removeListener?.("accountsChanged", handlers.accountsChanged);
    if (handlers.chainChanged) current.removeListener?.("chainChanged", handlers.chainChanged);
  };
}

export async function switchWalletNetwork(network: WalletNetworkParams): Promise<void> {
  const current = getWalletProvider();
  if (!current) throw new Error("Install MetaMask to switch networks.");
  try {
    await current.request({ method: "wallet_switchEthereumChain", params: [{ chainId: network.chainId }] });
  } catch (error) {
    const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
    if (code !== "4902") throw error instanceof Error ? error : new Error("Wallet network switch failed.");
    await current.request({ method: "wallet_addEthereumChain", params: [network] });
    await current.request({ method: "wallet_switchEthereumChain", params: [{ chainId: network.chainId }] });
  }
}

export async function connectWallet(): Promise<string> {
  const current = getWalletProvider();
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

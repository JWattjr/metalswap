import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Next's development compiler can race while several static JSON-backed proof
  // pages are compiled for the first time. Serial execution keeps this release
  // check deterministic; the suite is intentionally small.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run dev -- --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_GENLAYER_RPC_URL: "",
      NEXT_PUBLIC_GENLAYER_NETWORK: "Synthetic Replay",
      NEXT_PUBLIC_METALSWAP_ADDRESS: "",
      NEXT_PUBLIC_SETTLEMENT_GATE_ADDRESS: "",
    },
  },
});

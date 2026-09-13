# Observed deployment

Captured on 2026-09-13 from the configured account `0xdB433ff614bDD1ecE21Aa97221C3E0a7ecf79c92`.

- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- RPC: `https://studio.genlayer.com/api`
- Frontend: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Vercel deployment: [ready production build](https://vercel.com/wattxs-projects/metal-swap/BestKUnZoUaHSGYrHkwfRdHPZbnW)
- MetalSwap: `0xB615a841A33e79CC9EDB67D7dcf7C42eEeE0ce7E`
- SettlementGate: `0x88862E86176887CE7fc611EEe3105b00eCcaac17`
- Frozen evidence source: `https://metal-swap.vercel.app/evidence/`
- Market at readback: `market-2026-09-13T22:30:00Z`
- Market interval: `2026-09-13T22:30:00Z → 2026-09-13T22:45:00Z`
- Settlement deadline: `2026-09-13T22:55:00Z`
- Market status at readback: `UPCOMING`
- Settlement gate: configured; finalized market records at capture: `0`

Every deployment/configuration receipt below was independently awaited at `FINALIZED` and reported `SUCCESS` by the deployment script:

| Step | Transaction |
| --- | --- |
| Deploy SettlementGate | `0x4199beff0cb7ff6387395ea7a63f29f1a8f55f885b447879de5fdc5ec2c474ef` |
| Deploy MetalSwap | `0x75bf3854c2bc4cf4f7b3c75e4bed39d4826fcb8727327e2fa2b5731e905f2f70` |
| Bind gate → market | `0x15a918a6b02580a040c8df527cd9d0bf9b9e568e94a753d9eead5eae9d9ee947` |
| Bind market → gate | `0x3920264a6d4dc8b892fad3c236f01f016d01c2f8e74ad4295feeb771aeb1970e` |
| Freeze evidence source | `0x92bb90d3809be6ab165e0945734629d8eaeb9bffc4ed49cd51d420b4ec48b593` |
| Open next UTC market | `0xfa7dafc0be0c6ea6acb2d1ea888e409bcf7d743701aaa7c8c4df37882edb3ccf` |

The raw machine-readable record is in `deploy/last-deployment.json`. This is a synthetic-evidence demo deployment; it is not a claim that live XAUS/AlyawmGold data is settlement-grade.

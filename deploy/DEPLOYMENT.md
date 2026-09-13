# Observed deployment

Captured on 2026-09-13 from the configured account `0x2c8eb5db1105a85be66badafed88d10cf393cdd8`.

- Network: GenLayer Studio Network (`studionet`), chain ID `61999`
- RPC: `https://studio.genlayer.com/api`
- Frontend: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Vercel deployment: [ready production build](https://vercel.com/wattxs-projects/metal-swap/ohNSmWedjjFx2Q4Ez2LorKG7Gow2)
- MetalSwap: `0x7d50E2da8375FFF65Ff7FF513Ea977aa38188B2f`
- SettlementGate: `0xF0E2eF57E368adB64E6da5Af0Fd256d7457C2581`
- Frozen evidence source: `https://metal-swap.vercel.app/evidence/`
- Market at readback: `market-2026-09-13T21:15:00Z`
- Market interval: `2026-09-13T21:15:00Z → 2026-09-13T21:30:00Z`
- Settlement deadline: `2026-09-13T21:40:00Z`
- Market status at readback: `UPCOMING`
- Settlement gate: configured; finalized market records at capture: `0`

Every deployment/configuration receipt below was independently awaited at `FINALIZED` and reported `SUCCESS` by the deployment script:

| Step | Transaction |
| --- | --- |
| Deploy SettlementGate | `0x2ef2c372c7e2c374f8275eb085fdd4a6ee8ccc11ebbac7cee24309c31b27fa8f` |
| Deploy MetalSwap | `0x4a4a051f701e055a13fd52e7bb5422adc13c09f6e3f9f32e524d08927e86e7a7` |
| Bind gate → market | `0x1b123c4afe897b586a055d7d004affc3dbe7cf0f6300a8c3ef846e27e2176082` |
| Bind market → gate | `0x7dc19a1a7ffeef38d5abc6bac63b5b6ae9f611edb7aef7e72b57418571aa1208` |
| Freeze evidence source | `0x658f4c486eae30e990f6a0cae498edc12b4f4e3d340442b731d4d17f4abee283` |
| Open next UTC market | `0xb4b303381862c7284abac35a229a84ca7c9f11076cf794ae813874923844c8ce` |

The raw machine-readable record is in `deploy/last-deployment.json`. This is a synthetic-evidence demo deployment; it is not a claim that live XAUS/AlyawmGold data is settlement-grade.

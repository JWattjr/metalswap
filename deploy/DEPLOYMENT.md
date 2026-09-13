# Observed deployment

Captured on 2026-09-13 from the configured account `0x2c8eb5db1105a85be66badafed88d10cf393cdd8`.

- Network: GenLayer Studio Network (`studionet`)
- Frontend: [metal-swap.vercel.app](https://metal-swap.vercel.app)
- Vercel deployment: [ready production build](https://vercel.com/wattxs-projects/metal-swap/5PNNd9PpUvpHAw7B9GRs6B2hwmM8)
- MetalSwap: `0x1Ad6b4643DCd04AA774a0AD3305c7d3F555EfDDc`
- SettlementGate: `0x85481500d587A29b523c512FCB7fbCc347FC28a9`
- Frozen evidence source: `https://metal-swap.vercel.app/evidence/`
- First market: `market-2026-09-13T18:45:00Z`
- Market interval: `2026-09-13T18:45:00Z → 2026-09-13T19:00:00Z`
- Market status at readback: `UPCOMING`
- Settlement gate: configured; finalized market records at capture: `0`

Every deployment/configuration receipt below was independently awaited at `FINALIZED` and reported `SUCCESS` by the deployment script:

| Step | Transaction |
| --- | --- |
| Deploy SettlementGate | `0xc0495e952994b3d15ae8dd863a258cba7a6e8e5fd3927504bbcb3c4f51098175` |
| Deploy MetalSwap | `0x2a1ae6fc2fc9be3ccf4bc387cb143d0971e9e27744c9a5737c183569e04fac1d` |
| Bind gate → market | `0x52b04fb0ba47ee5e1fcc804d711a2f477df99926915a82e507ec08d0a1cce5c9` |
| Bind market → gate | `0x7d71dc10ee9158c026fb5bdb66ca4330b485341ac6a4f9cffe3bce55fbf4bdfb` |
| Freeze evidence source | `0x312d087aaf5a07e979777177f27b7729d854ad74b6f4ba4714ae81c3575b8e75` |
| Open first market | `0x844bc37eba5abcfcb5c4a34e237295eb4d99909bde060480e425df73966602c0` |

The raw machine-readable record is in `deploy/last-deployment.json`. This is a synthetic-evidence demo deployment; it is not a claim that live XAUS/AlyawmGold data is settlement-grade.

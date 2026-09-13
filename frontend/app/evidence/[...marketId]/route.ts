import { NextResponse } from "next/server";

import { makeSyntheticEvidence } from "@/lib/syntheticEvidence";

export const dynamic = "force-dynamic";

export function GET(request: Request, context: { params: Promise<{ marketId: string[] }> }) {
  return context.params.then(({ marketId }) => {
    const rawMarketId = marketId.join("/");
    const normalizedMarketId = rawMarketId.endsWith(".json")
      ? rawMarketId.slice(0, -".json".length)
      : rawMarketId;
    const origin = new URL(request.url).origin;
    const evidence = makeSyntheticEvidence(normalizedMarketId, origin);
    if (!evidence) {
      return NextResponse.json({ error: "Unknown synthetic market id" }, { status: 404 });
    }
    return NextResponse.json(evidence, {
      headers: {
        "cache-control": "public, max-age=30, s-maxage=30",
        "x-metalswap-data-mode": "synthetic-evidence-demo",
      },
    });
  });
}

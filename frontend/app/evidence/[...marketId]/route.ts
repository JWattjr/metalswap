import { NextResponse } from "next/server";

import {
  makePendingSyntheticEvidence,
  makeSyntheticEvidence,
  parseSyntheticMarketStart,
} from "@/lib/syntheticEvidence";

export const dynamic = "force-dynamic";

export function GET(request: Request, context: { params: Promise<{ marketId: string[] }> }) {
  return context.params.then(({ marketId }) => {
    const rawMarketId = marketId.join("/");
    const normalizedMarketId = rawMarketId.endsWith(".json")
      ? rawMarketId.slice(0, -".json".length)
      : rawMarketId;
    const origin = new URL(request.url).origin;
    const start = parseSyntheticMarketStart(normalizedMarketId);
    const evidence = makeSyntheticEvidence(normalizedMarketId, origin);
    if (!start || !evidence) {
      return NextResponse.json({ error: "Unknown synthetic market id" }, { status: 404 });
    }
    const endMs = Date.parse(start) + 900_000;
    if (Date.now() < endMs) {
      const pending = makePendingSyntheticEvidence(normalizedMarketId, origin);
      return NextResponse.json(pending, {
        headers: {
          "cache-control": "no-store",
          "x-metalswap-data-mode": "synthetic-evidence-demo",
          "x-metalswap-evidence-state": "not-yet-available",
        },
      });
    }
    return NextResponse.json(evidence, {
      headers: {
        "cache-control": "public, max-age=60, s-maxage=60",
        "x-metalswap-data-mode": "synthetic-evidence-demo",
      },
    });
  });
}

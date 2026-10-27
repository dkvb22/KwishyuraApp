import { requireShopkeeper } from "../../../lib/session"; import { csvForShop } from "../../../lib/db";
export async function GET(req: Request) {
  const { shop } = await requireShopkeeper(); const u = new URL(req.url), ok = (v: string | null) => (v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined);
  return new Response(csvForShop(shop.id, ok(u.searchParams.get("from")), ok(u.searchParams.get("to"))), { headers: { "content-type": "text/csv; charset=utf-8", "content-disposition": 'attachment; filename="kwishyura-transactions.csv"', "cache-control": "no-store" } });
}

import { getProvider } from "../../../../lib/payments/provider"; import { processProviderEvent } from "../../../../lib/db";
export async function POST(req: Request) {
  const raw = await req.text(), p = getProvider();
  const ev = p.verifyWebhook(raw, req.headers.get("x-signature")); // authenticity first; never trust the body otherwise
  if (!ev) return Response.json({ error: "invalid signature or payload" }, { status: 401 });
  return Response.json({ result: processProviderEvent(ev, p.name) });
}

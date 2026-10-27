import { scheduleReminders, processSmsQueue } from "../../../../lib/db"; import { getSmsProvider } from "../../../../lib/sms";
export async function POST(req: Request) {
  const s = process.env.CRON_SECRET; if (!s) return Response.json({ error: "CRON_SECRET not configured" }, { status: 503 });
  if (req.headers.get("authorization") !== `Bearer ${s}`) return Response.json({ error: "unauthorized" }, { status: 401 });
  return Response.json({ queued: scheduleReminders(), sent: await processSmsQueue(getSmsProvider()) });
}

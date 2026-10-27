// Background worker: run with `npm run worker`. Does not depend on any browser tab.
import { scheduleReminders, processSmsQueue } from "../src/lib/db"; import { getSmsProvider } from "../src/lib/sms";
async function tick() { const q = scheduleReminders(), s = await processSmsQueue(getSmsProvider()); console.log(`[worker] ${new Date().toISOString()} queued=${q} sent=${s}`); }
await tick(); setInterval(() => tick().catch(e => console.error("[worker] error", e)), 60_000);

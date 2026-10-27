export interface SmsProvider { name: string; isSimulation: boolean; send(a: { to: string; body: string }): Promise<{ id: string }> }
/** Development provider: writes to the server console only. NO real SMS is sent. */
export const devLogSms: SmsProvider = { name: "DEV_LOG", isSimulation: true,
  async send({ to, body }) { console.log(`[DEV SMS - NOT SENT] to=${to} body="${body}"`); return { id: "DEV-" + Date.now() }; } };
export function getSmsProvider(): SmsProvider {
  const p = process.env.SMS_PROVIDER ?? "dev-log";
  if (p === "dev-log") return devLogSms;
  throw new Error(`SMS provider "${p}" is not implemented. Add an adapter implementing SmsProvider (see README).`);
}

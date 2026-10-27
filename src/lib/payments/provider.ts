import { createHmac, timingSafeEqual, randomBytes } from "node:crypto";
import { z } from "zod";
export type PayStatus = "SUCCESSFUL" | "FAILED" | "CANCELLED" | "PENDING";
export interface ProviderEvent { eventId: string; providerRef: string; status: PayStatus; amount: number; currency: string }
export interface PaymentProvider {
  name: string; isSimulation: boolean;
  initiate(a: { reference: string; amount: number; currency: string; payerPhone: string }): Promise<{ providerRef: string }>;
  /** Returns the event only if the signature is authentic and the body is well-formed; otherwise null. */
  verifyWebhook(raw: string, signature: string | null): ProviderEvent | null;
}
const secret = () => { const s = process.env.SANDBOX_WEBHOOK_SECRET ?? (process.env.NODE_ENV === "production" ? "" : "sandbox-dev-secret"); if (!s) throw new Error("SANDBOX_WEBHOOK_SECRET is not set"); return s; };
export const signSandbox = (raw: string) => createHmac("sha256", secret()).update(raw).digest("hex");
const shape = z.object({ eventId: z.string().min(6), providerRef: z.string().min(3), status: z.enum(["SUCCESSFUL", "FAILED", "CANCELLED", "PENDING"]), amount: z.number().int(), currency: z.string().length(3) });

/** SIMULATION ONLY. Not MTN MoMo. No money moves and no real phone is contacted. */
export const sandboxProvider: PaymentProvider = {
  name: "SANDBOX", isSimulation: true,
  async initiate() { return { providerRef: "SBX-" + randomBytes(6).toString("hex").toUpperCase() }; },
  verifyWebhook(raw, signature) {
    if (!signature) return null;
    const want = Buffer.from(signSandbox(raw)), got = Buffer.from(signature);
    if (want.length !== got.length || !timingSafeEqual(want, got)) return null;
    try { const r = shape.safeParse(JSON.parse(raw)); return r.success ? r.data : null; } catch { return null; }
  },
};
export function getProvider(): PaymentProvider {
  const p = process.env.PAYMENT_PROVIDER ?? "sandbox";
  if (p === "sandbox") return sandboxProvider;
  throw new Error(`Payment provider "${p}" is not implemented. Add credentials and an adapter implementing PaymentProvider (see README) before enabling it.`);
}

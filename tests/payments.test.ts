import { describe, it, expect } from "vitest";
process.env.KW_DB = ":memory:";
const m = await import("../src/lib/db"); const { sandboxProvider: sp, signSandbox } = await import("../src/lib/payments/provider");
const shop = await m.registerShopkeeper({ name: "S", shopName: "Shop", phone: "+250788000031", password: "password1" });
const cid = m.createCustomer(shop.shopId, shop.userId, "Cust", "+250788555555");
m.recordSale({ shopId: shop.shopId, customerId: cid, actor: shop.userId, description: "Item", quantity: 1, unitPrice: 5000, key: "sale-p-001" });
const user = await m.registerCustomerUser({ name: "Cust", phone: "+250788555555", password: "password1" });
m.linkByInvite(user.userId, (m.getCustomer(shop.shopId, cid) as any).invite_code);
let n = 0;
const start = async (amount: number, ttlMs?: number) => { const reference = m.newPaymentRef(), { providerRef } = await sp.initiate({ reference, amount, currency: "RWF", payerPhone: "x" });
  m.createPaymentAttempt({ userId: user.userId, customerId: cid, amount, reference, provider: "SANDBOX", providerRef, ttlMs }); return { reference, providerRef }; };
const ev = (providerRef: string, status: any, amount = 2000, eventId = `EVT-${++n}-abcdef`) => ({ eventId, providerRef, status, amount, currency: "RWF" });
const bal = () => m.balance(shop.shopId, cid);
describe("sandbox payments", () => {
  it("pending attempt changes no balance; rejects overpayment", async () => {
    const p = await start(2000); expect(bal()).toBe(5000); expect(m.attemptForUser(user.userId, p.reference)!.status).toBe("PENDING");
    await expect(start(5001)).rejects.toThrow(/cannot pay more/);
    expect(m.processProviderEvent(ev(p.providerRef, "PENDING"), "SANDBOX")).toBe("pending"); expect(bal()).toBe(5000);
  });
  it("verified success creates one confirmed repayment; duplicate and replay events change nothing", async () => {
    const p = await start(2000), e = ev(p.providerRef, "SUCCESSFUL");
    expect(m.processProviderEvent(e, "SANDBOX")).toBe("confirmed"); expect(bal()).toBe(3000);
    expect(m.processProviderEvent(e, "SANDBOX")).toBe("duplicate");
    expect(m.processProviderEvent(ev(p.providerRef, "SUCCESSFUL"), "SANDBOX")).toBe("ignored"); expect(bal()).toBe(3000);
    expect((m.attemptForUser(user.userId, p.reference) as any).receipt_ref).toMatch(/^KW-/);
  });
  it("failed, cancelled and unknown events never create repayments", async () => {
    const f = await start(1000), c = await start(1000);
    expect(m.processProviderEvent(ev(f.providerRef, "FAILED", 1000), "SANDBOX")).toBe("failed");
    expect(m.processProviderEvent(ev(c.providerRef, "CANCELLED", 1000), "SANDBOX")).toBe("cancelled");
    expect(m.processProviderEvent(ev("SBX-NOPE", "SUCCESSFUL"), "SANDBOX")).toBe("unknown_payment"); expect(bal()).toBe(3000);
  });
  it("wrong amount goes to review, not the ledger; late success after timeout is honoured", async () => {
    const w = await start(1000); expect(m.processProviderEvent(ev(w.providerRef, "SUCCESSFUL", 999), "SANDBOX")).toBe("review"); expect(bal()).toBe(3000);
    const t = await start(1000); m.forceExpire(t.reference); expect(m.attemptForUser(user.userId, t.reference)!.status).toBe("EXPIRED");
    expect(m.processProviderEvent(ev(t.providerRef, "SUCCESSFUL", 1000), "SANDBOX")).toBe("confirmed"); expect(bal()).toBe(2000);
  });
  it("success that would overpay (cash paid meanwhile) goes to review", async () => {
    const p = await start(2000); m.recordRepayment({ shopId: shop.shopId, customerId: cid, actor: shop.userId, amount: 1500, method: "CASH", key: "cash-p-001" });
    expect(m.processProviderEvent(ev(p.providerRef, "SUCCESSFUL"), "SANDBOX")).toBe("review"); expect(bal()).toBe(500);
  });
  it("webhook signature: forged or tampered bodies are rejected", () => {
    const raw = JSON.stringify(ev("SBX-ABC", "SUCCESSFUL"));
    expect(sp.verifyWebhook(raw, signSandbox(raw))).not.toBeNull();
    expect(sp.verifyWebhook(raw, "deadbeef")).toBeNull(); expect(sp.verifyWebhook(raw, null)).toBeNull();
    expect(sp.verifyWebhook(raw.replace("2000", "9000"), signSandbox(raw))).toBeNull();
  });
  it("other customers cannot read the attempt", async () => {
    const other = await m.registerCustomerUser({ name: "O", phone: "+250788666666", password: "password1" });
    const p = await start(100); expect(m.attemptForUser(other.userId, p.reference)).toBeUndefined();
  });
});

import { describe, it, expect } from "vitest";
process.env.KW_DB = ":memory:";
const m = await import("../src/lib/db"); const { devLogSms } = await import("../src/lib/sms");
const day = (n: number) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
const shop = await m.registerShopkeeper({ name: "S", shopName: "Demo Shop", phone: "+250788000041", password: "password1" });
const cid = m.createCustomer(shop.shopId, shop.userId, "Demo Customer", "+250788777777");
const sale = (key: string, dueDate?: string, p = 1000) => m.recordSale({ shopId: shop.shopId, customerId: cid, actor: shop.userId, description: "SecretItem", quantity: 1, unitPrice: p, dueDate, key });
const rows = () => m.listSms(shop.shopId);
describe("sms reminders", () => {
  it("queues one upcoming reminder, never duplicates, with safe content", () => {
    sale("sale-s-0001", day(1));
    expect(m.scheduleReminders()).toBe(1); expect(m.scheduleReminders()).toBe(0);
    const r = m.db.prepare("SELECT body FROM sms_notifications WHERE kind='UPCOMING'").get() as any;
    expect(r.body).toContain("outstanding balance of 1,000 RWF"); expect(r.body).not.toMatch(/SecretItem|password/i);
  });
  it("overdue reminders repeat at most weekly", () => {
    sale("sale-s-0002", day(-3), 500);
    const now = new Date(); expect(m.scheduleReminders(now)).toBe(1); expect(m.scheduleReminders(now)).toBe(0);
    expect(m.scheduleReminders(new Date(+now + 8 * 864e5))).toBeGreaterThanOrEqual(1);
    expect(m.shopOverdue(shop.shopId)).toBe(500);
  });
  it("dev-log provider marks SENT without any real gateway", async () => {
    expect(await m.processSmsQueue(devLogSms)).toBeGreaterThan(0);
    expect(rows().every((r: any) => r.status === "SENT" && r.provider === "DEV_LOG")).toBe(true);
  });
  it("retries with backoff then fails after 5 attempts; errors recorded", async () => {
    sale("sale-s-0003"); m.recordRepayment({ shopId: shop.shopId, customerId: cid, actor: shop.userId, amount: 100, method: "CASH", key: "cash-s-001" });
    const bad = { name: "BAD", isSimulation: false, send: async () => { throw new Error("gateway down"); } };
    const t0 = new Date(); expect(await m.processSmsQueue(bad, t0)).toBe(0);
    const f = m.db.prepare("SELECT attempts,status,error,next_attempt_at FROM sms_notifications WHERE status='QUEUED'").get() as any;
    expect(f.attempts).toBe(1); expect(f.error).toMatch(/gateway down/); expect(Date.parse(f.next_attempt_at)).toBeGreaterThan(+t0);
    expect(await m.processSmsQueue(bad, t0)).toBe(0); expect((m.db.prepare("SELECT attempts FROM sms_notifications WHERE status='QUEUED'").get() as any).attempts).toBe(1);
    for (let i = 1; i <= 5; i++) await m.processSmsQueue(bad, new Date(+t0 + i * 3600e3));
    expect((m.db.prepare("SELECT status FROM sms_notifications WHERE error LIKE '%gateway%'").get() as any).status).toBe("FAILED");
  });
  it("no reminder for fully paid debts", () => {
    const total = m.balance(shop.shopId, cid); m.recordRepayment({ shopId: shop.shopId, customerId: cid, actor: shop.userId, amount: total, method: "CASH", key: "cash-s-002" });
    expect(m.scheduleReminders(new Date(Date.now() + 30 * 864e5))).toBe(0);
  });
});
describe("disputes, csv, reset", () => {
  it("only the linked customer can dispute their own transaction", async () => {
    const u = await m.registerCustomerUser({ name: "C", phone: "+250788777777", password: "password1" }); m.linkByInvite(u.userId, (m.getCustomer(shop.shopId, cid) as any).invite_code);
    const o = await m.registerCustomerUser({ name: "O", phone: "+250788888888", password: "password1" }); const e = m.history(shop.shopId, cid)[0];
    expect(() => m.createDispute(o.userId, cid, e.id, "this is wrong")).toThrow(/Account not found/);
    const id = m.createDispute(u.userId, cid, e.id, "I did not buy this"); expect(m.disputesFor(shop.shopId, cid)).toHaveLength(1);
    m.resolveDispute(shop.shopId, id, shop.userId, "Checked and corrected"); expect(m.disputesFor(shop.shopId, cid)[0].status).toBe("RESOLVED");
  });
  it("csv neutralises formulas and respects dates", () => {
    expect(m.csvCell("=1+1")).toBe("'=1+1"); expect(m.csvCell('a,"b"')).toBe('"a,""b"""');
    expect(m.csvForShop(shop.shopId).split("\n").length).toBeGreaterThan(2); expect(m.csvForShop(shop.shopId, "2999-01-01").split("\n")).toHaveLength(1);
  });
  it("reset token is single-use and expires safely", async () => {
    m.requestPasswordReset("+250788000041", "http://x"); const body = (m.db.prepare("SELECT body FROM sms_notifications WHERE kind='PASSWORD_RESET'").get() as any).body as string;
    const tok = body.match(/reset\/([a-f0-9]+)/)![1];
    await expect(m.resetPassword("nope", "newpassword1")).rejects.toThrow(/invalid or has expired/);
    await m.resetPassword(tok, "newpassword1"); expect(await m.verifyLogin("+250788000041", "newpassword1")).not.toBeNull();
    await expect(m.resetPassword(tok, "another-pass1")).rejects.toThrow(/invalid or has expired/);
  });
});

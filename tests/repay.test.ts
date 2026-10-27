import { describe, it, expect } from "vitest";
process.env.KW_DB = ":memory:";
const m = await import("../src/lib/db");
const a = await m.registerShopkeeper({ name: "A", shopName: "SA", phone: "+250788000011", password: "password1" });
const b = await m.registerShopkeeper({ name: "B", shopName: "SB", phone: "+250788000012", password: "password1" });
const c = m.createCustomer(a.shopId, a.userId, "Cust", "+250788222222");
const sale = (key: string, p: number) => m.recordSale({ shopId: a.shopId, customerId: c, actor: a.userId, description: "Item", quantity: 1, unitPrice: p, key });
const pay = (key: string, amount: number) => m.recordRepayment({ shopId: a.shopId, customerId: c, actor: a.userId, amount, method: "CASH", key });
describe("repayments and reversals", () => {
  it("partial then full repayment; overpayment and invalid amounts rejected", () => {
    const s1 = sale("sale-0001", 5000);
    pay("pay-00001", 2000); expect(m.balance(a.shopId, c)).toBe(3000);
    expect(() => pay("pay-00002", 3001)).toThrow(/more than/); expect(() => pay("pay-00003", 0)).toThrow(/Invalid/);
    pay("pay-00004", 3000); expect(m.balance(a.shopId, c)).toBe(0); expect(s1.amount).toBe(5000);
  });
  it("duplicate repayment key does not double-count", () => {
    sale("sale-0002", 1000); pay("pay-00005", 400); expect(pay("pay-00005", 400).duplicate).toBe(true); expect(m.balance(a.shopId, c)).toBe(600);
  });
  it("reversals are append-only, excluded from balance, and guarded", () => {
    const p = m.history(a.shopId, c).find(r => r.reference && r.type === "REPAYMENT" && r.amount === 400)!;
    const before = m.history(a.shopId, c).length;
    m.reverseEntry({ shopId: a.shopId, entryId: p.id, actor: a.userId, reason: "Entered wrong" });
    expect(m.history(a.shopId, c).length).toBe(before + 1); expect(m.balance(a.shopId, c)).toBe(1000);
    expect(() => m.reverseEntry({ shopId: a.shopId, entryId: p.id, actor: a.userId, reason: "again" })).toThrow(/Already/);
    expect(() => m.reverseEntry({ shopId: b.shopId, entryId: p.id, actor: b.userId, reason: "other shop" })).toThrow(/cannot be reversed/);
  });
  it("distinct totals: repayments are not sales", () => {
    expect(m.shopTotals(a.shopId)).toEqual({ credit: 6000, repaid: 5000, outstanding: 1000 });
  });
});

import { describe, it, expect } from "vitest";
import { Ledger, LedgerError } from "../src/lib/ledger";
const S = "shopA", C = "cust1", B = "user1";
const sale = (l: Ledger, q: number, p: number, extra = {}) => l.recordCreditSale({ shopId: S, customerId: C, quantity: q, unitPrice: p, by: B, ...extra });

describe("ledger", () => {
  it("calculates totals and balance on the server side", () => {
    const l = new Ledger(); expect(sale(l, 3, 500).amount).toBe(1500); sale(l, 1, 2000);
    expect(l.balance(S, C)).toBe(3500);
  });
  it("handles partial and full repayments", () => {
    const l = new Ledger(); sale(l, 1, 5000);
    l.recordRepayment({ shopId: S, customerId: C, amount: 2000, by: B }); expect(l.balance(S, C)).toBe(3000);
    l.recordRepayment({ shopId: S, customerId: C, amount: 3000, by: B }); expect(l.balance(S, C)).toBe(0);
  });
  it("rejects invalid and excessive repayments", () => {
    const l = new Ledger(); sale(l, 1, 1000);
    expect(() => l.recordRepayment({ shopId: S, customerId: C, amount: 0, by: B })).toThrow(LedgerError);
    expect(() => l.recordRepayment({ shopId: S, customerId: C, amount: 1.5, by: B })).toThrow(LedgerError);
    expect(() => l.recordRepayment({ shopId: S, customerId: C, amount: 1001, by: B })).toThrow(/exceeds/);
  });
  it("reversal is append-only and excluded from balance", () => {
    const l = new Ledger(); const s = sale(l, 1, 1000); const n = l.entries.length;
    l.reverse(s.id, S, B);
    expect(l.entries.length).toBe(n + 1); expect(l.balance(S, C)).toBe(0);
    expect(() => l.reverse(s.id, S, B)).toThrow(/Already/);
  });
  it("pending and failed payments do not count", () => {
    const l = new Ledger(); sale(l, 1, 1000);
    l.recordRepayment({ shopId: S, customerId: C, amount: 500, by: B, status: "PENDING" });
    l.recordRepayment({ shopId: S, customerId: C, amount: 500, by: B, status: "FAILED" });
    expect(l.balance(S, C)).toBe(1000);
  });
  it("duplicate submissions with same idempotency key create one entry", () => {
    const l = new Ledger(); sale(l, 1, 1000, { idempotencyKey: "k1" }); sale(l, 1, 1000, { idempotencyKey: "k1" });
    expect(l.balance(S, C)).toBe(1000);
  });
  it("isolates shops and allocates FIFO with debt states", () => {
    const l = new Ledger(); sale(l, 1, 1000); sale(l, 1, 2000, { dueDate: new Date("2020-01-01") });
    l.recordRepayment({ shopId: S, customerId: C, amount: 1500, by: B });
    expect(l.balance("shopB", C)).toBe(0);
    expect(l.debts(S, C).map(d => d.state)).toEqual(["Paid", "Overdue"]);
    expect(l.debts(S, C)[1].remaining).toBe(1500);
  });
});

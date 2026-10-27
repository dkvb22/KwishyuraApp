import { describe, it, expect } from "vitest";
process.env.KW_DB = ":memory:";
const m = await import("../src/lib/db");
describe("db layer", async () => {
  const a = await m.registerShopkeeper({ name: "Demo A", shopName: "Shop A", phone: "+250788000001", password: "password1" });
  const b = await m.registerShopkeeper({ name: "Demo B", shopName: "Shop B", phone: "+250788000002", password: "password1" });
  const cid = m.createCustomer(a.shopId, a.userId, "Cust One", "+250788111111");
  const sale = (key: string, q = 2, p = 500) => m.recordSale({ shopId: a.shopId, customerId: cid, actor: a.userId, description: "Rice", quantity: q, unitPrice: p, key });
  it("rejects duplicate phone and logs in", async () => {
    await expect(m.registerShopkeeper({ name: "X", shopName: "Y", phone: "+250788000001", password: "password1" })).rejects.toThrow(/already/);
    expect(await m.verifyLogin("+250788000001", "password1")).toMatchObject({ role: "SHOPKEEPER" });
    expect(await m.verifyLogin("+250788000001", "wrong")).toBeNull();
  });
  it("records sale, server total, balance; duplicate key is idempotent", () => {
    expect(sale("key-00001").amount).toBe(1000); expect(sale("key-00001").duplicate).toBe(true);
    expect(m.balance(a.shopId, cid)).toBe(1000); sale("key-00002", 1, 250); expect(m.balance(a.shopId, cid)).toBe(1250);
  });
  it("isolates shops (no cross-shop read or write)", () => {
    expect(m.getCustomer(b.shopId, cid)).toBeUndefined();
    expect(() => m.recordSale({ shopId: b.shopId, customerId: cid, actor: b.userId, description: "x", quantity: 1, unitPrice: 1, key: "key-00003" })).toThrow(/not found/);
  });
});

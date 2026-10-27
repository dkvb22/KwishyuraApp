import { describe, it, expect } from "vitest";
process.env.KW_DB = ":memory:";
const m = await import("../src/lib/db");
const shop = await m.registerShopkeeper({ name: "S", shopName: "Demo Shop", phone: "+250788000021", password: "password1" });
const P = "+250788333333";
const cid = m.createCustomer(shop.shopId, shop.userId, "Demo Customer", P);
m.recordSale({ shopId: shop.shopId, customerId: cid, actor: shop.userId, description: "Rice", quantity: 2, unitPrice: 750, key: "sale-c-001" });
const code = (m.getCustomer(shop.shopId, cid) as any).invite_code as string;
const cust = await m.registerCustomerUser({ name: "Demo Customer", phone: P, password: "password1" });
const other = await m.registerCustomerUser({ name: "Someone Else", phone: "+250788444444", password: "password1" });
describe("customer linking and access", () => {
  it("phone alone exposes nothing", () => { expect(m.customerAccounts(cust.userId)).toEqual([]); });
  it("code issued for another phone is refused", () => {
    expect(() => m.linkByInvite(other.userId, code)).toThrow(/Invalid or already used/);
    expect(() => m.linkByInvite(cust.userId, "WRONGCODE")).toThrow(/Invalid or already used/);
  });
  it("matching phone + code links once; customer sees same balance as shop", () => {
    expect(m.linkByInvite(cust.userId, code.toLowerCase())).toBe(cid);
    const a = m.customerAccounts(cust.userId); expect(a).toHaveLength(1);
    expect(a[0].balance).toBe(1500); expect(a[0].balance).toBe(m.balance(shop.shopId, cid));
    expect(() => m.linkByInvite(cust.userId, code)).toThrow(/Invalid or already used/);
  });
  it("customers cannot open each other's accounts by id", () => {
    expect(m.customerAccount(cust.userId, cid)).toBeDefined();
    expect(m.customerAccount(other.userId, cid)).toBeUndefined();
  });
});

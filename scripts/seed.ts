// Fictional demo data only. Safe to re-run (skips if the demo shopkeeper exists).
import * as m from "../src/lib/db";
const PW = "DemoPass123!", day = (n: number) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
if (await m.verifyLogin("+250788000001", PW)) { console.log("Demo data already present."); process.exit(0); }
const s = await m.registerShopkeeper({ name: "Demo Shopkeeper", shopName: "Demo Shop (fictional)", phone: "+250788000001", password: PW });
const mk = (n: string, p: string) => m.createCustomer(s.shopId, s.userId, n, p);
const [c1, c2, c3] = [mk("Demo Customer One", "+250788000101"), mk("Demo Customer Two", "+250788000102"), mk("Demo Customer Three", "+250788000103")];
let k = 0; const sale = (c: string, d: string, q: number, p: number, due?: string) => m.recordSale({ shopId: s.shopId, customerId: c, actor: s.userId, description: d, quantity: q, unitPrice: p, dueDate: due, key: `seed-sale-${++k}-xx` });
sale(c1, "Rice 5kg", 2, 3500, day(3)); sale(c1, "Cooking oil 1L", 1, 2800, day(10)); sale(c2, "Sugar 1kg", 3, 1500, day(-5)); sale(c3, "Soap", 4, 600);
m.recordRepayment({ shopId: s.shopId, customerId: c1, actor: s.userId, amount: 2000, method: "CASH", key: "seed-pay-1-xx" });
const u = await m.registerCustomerUser({ name: "Demo Customer One", phone: "+250788000101", password: PW });
m.linkByInvite(u.userId, (m.getCustomer(s.shopId, c1) as any).invite_code);
console.log(`Seeded.\n Shopkeeper: +250788000001 / ${PW}\n Customer (linked): +250788000101 / ${PW}\n Unlinked customer invite codes: ${[c2, c3].map(c => `${(m.getCustomer(s.shopId, c) as any).name}=${(m.getCustomer(s.shopId, c) as any).invite_code}`).join(", ")}`);

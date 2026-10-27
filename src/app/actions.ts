"use server";
import { z } from "zod";
import { redirect } from "next/navigation";
import { registerShopkeeper, verifyLogin, createCustomer, recordSale, recordRepayment, reverseEntry, registerCustomerUser, linkByInvite, createPaymentAttempt, saveSettings, createDispute, resolveDispute, requestPasswordReset, resetPassword, processSmsQueue, newPaymentRef, processProviderEvent, attemptForUser, forceExpire, DomainError } from "../lib/db";
import { getSmsProvider } from "../lib/sms";
import { getProvider, signSandbox } from "../lib/payments/provider";
import { randomBytes } from "node:crypto";
import { createSession, destroySession, requireShopkeeper, requireCustomer } from "../lib/session";

const phone = z.string().trim().regex(/^\+[1-9]\d{7,14}$/, "Use international format, e.g. +250788123456");
const fail = (path: string, msg: string): never => redirect(`${path}${path.includes("?") ? "&" : "?"}e=${encodeURIComponent(msg)}`);
const msg = (e: unknown) => e instanceof z.ZodError ? e.issues[0].message : e instanceof DomainError ? e.message : "Something went wrong";
const attempts = new Map<string, { n: number; t: number }>(); // dev-grade limiter; use shared store in production

export async function register(fd: FormData) {
  let r;
  try {
    const v = z.object({ name: z.string().trim().min(2), shopName: z.string().trim().min(2), phone,
      email: z.string().trim().email().optional().or(z.literal("")), address: z.string().trim().optional(),
      password: z.string().min(8, "Password must be at least 8 characters") }).parse(Object.fromEntries(fd));
    r = await registerShopkeeper({ ...v, email: v.email || undefined });
  } catch (e) { return fail("/register", msg(e)); }
  await createSession(r.userId, "SHOPKEEPER"); redirect("/dashboard");
}
export async function login(fd: FormData) {
  const p = String(fd.get("phone") ?? "").trim(), a = attempts.get(p) ?? { n: 0, t: Date.now() };
  if (Date.now() - a.t > 900000) { a.n = 0; a.t = Date.now(); }
  if (a.n >= 5) return fail("/login", "Too many attempts. Try again in 15 minutes.");
  const u = await verifyLogin(p, String(fd.get("password") ?? ""));
  if (!u) { attempts.set(p, { n: a.n + 1, t: a.t }); return fail("/login", "Invalid phone number or password"); }
  attempts.delete(p); await createSession(u.id, u.role);
  redirect(u.role === "SHOPKEEPER" ? "/dashboard" : u.role === "CUSTOMER" ? "/customer" : "/login");
}
export async function logout() { await destroySession(); redirect("/login"); }

export async function addCustomer(fd: FormData) {
  const { userId, shop } = await requireShopkeeper(); let id;
  try { const v = z.object({ name: z.string().trim().min(2), phone }).parse(Object.fromEntries(fd)); id = createCustomer(shop.id, userId, v.name, v.phone); }
  catch (e) { return fail("/dashboard", msg(e)); }
  redirect(`/dashboard/customers/${id}?ok=Customer added`);
}
export async function addSale(fd: FormData) {
  const { userId, shop } = await requireShopkeeper(); const cid = String(fd.get("customerId")), back = `/dashboard/customers/${cid}`; let r;
  try {
    const v = z.object({ description: z.string().trim().min(2, "Describe the item"), quantity: z.coerce.number().int().positive("Quantity must be a whole number above 0"),
      unitPrice: z.coerce.number().int().positive("Unit price must be a whole number above 0"), dueDate: z.string().optional(), note: z.string().trim().max(300).optional(), key: z.string().min(8) }).parse(Object.fromEntries(fd));
    r = recordSale({ shopId: shop.id, customerId: cid, actor: userId, ...v, dueDate: v.dueDate || undefined });
  } catch (e) { return fail(back, msg(e)); }
  redirect(`${back}?ok=${encodeURIComponent(`Credit sale ${r.reference} recorded`)}`);
}

export async function addRepayment(fd: FormData) {
  const { userId, shop } = await requireShopkeeper(); const cid = String(fd.get("customerId")), back = `/dashboard/customers/${cid}`; let r;
  try {
    const v = z.object({ amount: z.coerce.number().int().positive("Amount must be a whole number above 0"), key: z.string().min(8) }).parse(Object.fromEntries(fd));
    r = recordRepayment({ shopId: shop.id, customerId: cid, actor: userId, amount: v.amount, method: "CASH", key: v.key });
  } catch (e) { return fail(back, msg(e)); }
  redirect(`${back}?ok=${encodeURIComponent(`Repayment ${r.reference} recorded`)}`);
}
export async function reverse(fd: FormData) {
  const { userId, shop } = await requireShopkeeper(); const cid = String(fd.get("customerId")), back = `/dashboard/customers/${cid}`; let r;
  try {
    const v = z.object({ entryId: z.string().min(1), reason: z.string().trim().min(3, "Please give a reason for the reversal").max(300) }).parse(Object.fromEntries(fd));
    r = reverseEntry({ shopId: shop.id, entryId: v.entryId, actor: userId, reason: v.reason });
  } catch (e) { return fail(back, msg(e)); }
  redirect(`${back}?ok=${encodeURIComponent(`Reversal ${r.reference} recorded`)}`);
}

export async function registerCustomer(fd: FormData) {
  let r;
  try {
    const v = z.object({ name: z.string().trim().min(2), phone, email: z.string().trim().email().optional().or(z.literal("")),
      password: z.string().min(8, "Password must be at least 8 characters") }).parse(Object.fromEntries(fd));
    r = await registerCustomerUser({ ...v, email: v.email || undefined });
  } catch (e) { return fail("/register/customer", msg(e)); }
  await createSession(r.userId, "CUSTOMER"); redirect("/customer");
}
export async function linkShop(fd: FormData) {
  const { userId } = await requireCustomer(); const k = "link:" + userId, a = attempts.get(k) ?? { n: 0, t: Date.now() };
  if (Date.now() - a.t > 900000) { a.n = 0; a.t = Date.now(); }
  if (a.n >= 5) return fail("/customer", "Too many attempts. Try again in 15 minutes.");
  try { linkByInvite(userId, String(fd.get("code") ?? "")); }
  catch (e) { attempts.set(k, { n: a.n + 1, t: a.t }); return fail("/customer", msg(e)); }
  redirect("/customer?ok=" + encodeURIComponent("Shop linked to your account"));
}

export async function startPayment(fd: FormData) {
  const { userId } = await requireCustomer(); const cid = String(fd.get("customerId")), back = `/customer/shops/${cid}`; let ref;
  try {
    const v = z.object({ amount: z.coerce.number().int().positive("Amount must be a whole number above 0") }).parse(Object.fromEntries(fd));
    const p = getProvider(), reference = newPaymentRef();
    const phoneRow = (await import("../lib/db")).db.prepare("SELECT phone FROM users WHERE id=?").get(userId) as { phone: string };
    const { providerRef } = await p.initiate({ reference, amount: v.amount, currency: "RWF", payerPhone: phoneRow.phone });
    ref = createPaymentAttempt({ userId, customerId: cid, amount: v.amount, reference, provider: p.name, providerRef });
  } catch (e) { return fail(back, e instanceof Error && !(e instanceof DomainError) && !(e instanceof z.ZodError) ? e.message : msg(e)); }
  redirect(`/customer/payments/${ref}`);
}
/** Sandbox only: builds a signed provider event and sends it through the same verification + processing path as a real webhook. */
export async function simulatePayment(fd: FormData) {
  const { userId } = await requireCustomer(); const ref = String(fd.get("ref")), outcome = String(fd.get("outcome")), p = getProvider();
  if (!p.isSimulation) return fail(`/customer/payments/${ref}`, "Simulation is disabled for this provider");
  const a = attemptForUser(userId, ref) as any; if (!a) redirect("/customer");
  if (outcome === "timeout") forceExpire(ref);
  else {
    const status = ({ success: "SUCCESSFUL", fail: "FAILED", cancel: "CANCELLED", pending: "PENDING" } as Record<string, any>)[outcome]; if (!status) return fail(`/customer/payments/${ref}`, "Unknown outcome");
    const raw = JSON.stringify({ eventId: "EVT-" + randomBytes(8).toString("hex"), providerRef: a.provider_ref, status, amount: a.amount, currency: a.currency });
    const ev = p.verifyWebhook(raw, signSandbox(raw)); if (ev) processProviderEvent(ev, p.name);
  }
  redirect(`/customer/payments/${ref}`);
}

export async function saveSms(fd: FormData) {
  const { shop } = await requireShopkeeper();
  try { saveSettings(shop.id, fd.get("newSale") === "on", Number(fd.get("days"))); } catch (e) { return fail("/dashboard/sms", msg(e)); }
  redirect("/dashboard/sms?ok=" + encodeURIComponent("Settings saved"));
}
export async function openDispute(fd: FormData) {
  const { userId } = await requireCustomer(); const cid = String(fd.get("customerId")), back = `/customer/shops/${cid}`;
  try { createDispute(userId, cid, String(fd.get("ledgerId")), String(fd.get("message") ?? "")); } catch (e) { return fail(back, msg(e)); }
  redirect(back + "?ok=" + encodeURIComponent("Your question was sent to the shop"));
}
export async function answerDispute(fd: FormData) {
  const { userId, shop } = await requireShopkeeper(); const cid = String(fd.get("customerId")), back = `/dashboard/customers/${cid}`;
  try { resolveDispute(shop.id, String(fd.get("disputeId")), userId, String(fd.get("response") ?? "")); } catch (e) { return fail(back, msg(e)); }
  redirect(back + "?ok=" + encodeURIComponent("Response sent"));
}
export async function forgot(fd: FormData) {
  const p = phone.safeParse(String(fd.get("phone") ?? "")); if (!p.success) return fail("/forgot", p.error.issues[0].message);
  requestPasswordReset(p.data, process.env.APP_URL ?? "http://localhost:3000"); await processSmsQueue(getSmsProvider());
  redirect("/forgot?ok=" + encodeURIComponent("If that number is registered, a reset link has been sent."));
}
export async function doReset(fd: FormData) {
  try { await resetPassword(String(fd.get("token")), String(fd.get("password") ?? "")); } catch (e) { return fail(`/reset/${fd.get("token")}`, msg(e)); }
  redirect("/login?ok=" + encodeURIComponent("Password changed. You can log in now."));
}

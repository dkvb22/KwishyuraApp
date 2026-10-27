import { randomUUID, randomBytes } from "node:crypto";
import bcrypt from "bcryptjs";
// Node's built-in SQLite, loaded at runtime so the bundler never touches it.
const { DatabaseSync } = process.getBuiltinModule("node:sqlite") as typeof import("node:sqlite");

function init() {
  const d = new DatabaseSync(process.env.KW_DB ?? "dev.db");
  d.exec(`PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, role TEXT NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE, email TEXT, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
  CREATE TABLE IF NOT EXISTS shops(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL, address TEXT, currency TEXT NOT NULL DEFAULT 'RWF');
  CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY, shop_id TEXT NOT NULL REFERENCES shops(id), name TEXT NOT NULL, phone TEXT NOT NULL, user_id TEXT REFERENCES users(id), active INTEGER NOT NULL DEFAULT 1, invite_code TEXT UNIQUE, UNIQUE(shop_id, phone));
  CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY, reference TEXT NOT NULL UNIQUE, shop_id TEXT NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id), type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'CONFIRMED', amount INTEGER NOT NULL, description TEXT, quantity INTEGER, unit_price INTEGER, due_date TEXT, note TEXT, related_id TEXT, idempotency_key TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')), UNIQUE(shop_id, idempotency_key));
  CREATE TABLE IF NOT EXISTS payment_attempts(id TEXT PRIMARY KEY, reference TEXT NOT NULL UNIQUE, shop_id TEXT NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id), initiated_by TEXT NOT NULL, amount INTEGER NOT NULL, currency TEXT NOT NULL, status TEXT NOT NULL, provider TEXT NOT NULL, provider_ref TEXT UNIQUE, expires_at TEXT NOT NULL, ledger_id TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
  CREATE TABLE IF NOT EXISTS provider_events(event_id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_ref TEXT, outcome TEXT, received_at TEXT NOT NULL DEFAULT (datetime('now')));
  CREATE TABLE IF NOT EXISTS sms_notifications(id TEXT PRIMARY KEY, shop_id TEXT, customer_id TEXT, kind TEXT NOT NULL, event_key TEXT NOT NULL UNIQUE, to_phone TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED', attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at TEXT NOT NULL, error TEXT, provider TEXT, sent_at TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
  CREATE TABLE IF NOT EXISTS shop_settings(shop_id TEXT PRIMARY KEY, sms_new_sale INTEGER NOT NULL DEFAULT 0, remind_days_before INTEGER NOT NULL DEFAULT 2);
  CREATE TABLE IF NOT EXISTS disputes(id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, customer_id TEXT NOT NULL, ledger_id TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', response TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
  CREATE TABLE IF NOT EXISTS password_resets(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
  CREATE INDEX IF NOT EXISTS ix_ledger_cust ON ledger(shop_id, customer_id);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id TEXT, action TEXT NOT NULL, entity_id TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));`);
  return d;
}
const g = globalThis as unknown as { __kw?: InstanceType<typeof DatabaseSync> };
export const db = (g.__kw ??= init());
type Row = Record<string, any>;
const q = (sql: string, ...p: any[]) => db.prepare(sql).all(...p) as Row[];
const one = (sql: string, ...p: any[]) => db.prepare(sql).get(...p) as Row | undefined;
const audit = (actor: string, action: string, entity?: string) => db.prepare("INSERT INTO audit(actor_id,action,entity_id) VALUES(?,?,?)").run(actor, action, entity ?? null);
function tx<T>(fn: () => T): T { db.exec("BEGIN IMMEDIATE"); try { const r = fn(); db.exec("COMMIT"); return r; } catch (e) { db.exec("ROLLBACK"); throw e; } }

export class DomainError extends Error {}

export async function registerShopkeeper(a: { name: string; shopName: string; phone: string; email?: string; address?: string; password: string }) {
  const hash = await bcrypt.hash(a.password, 12);
  return tx(() => {
    if (one("SELECT 1 FROM users WHERE phone=?", a.phone)) throw new DomainError("This phone number is already registered");
    const uid = randomUUID(), sid = randomUUID();
    db.prepare("INSERT INTO users(id,role,name,phone,email,password_hash) VALUES(?,?,?,?,?,?)").run(uid, "SHOPKEEPER", a.name, a.phone, a.email ?? null, hash);
    db.prepare("INSERT INTO shops(id,owner_id,name,address) VALUES(?,?,?,?)").run(sid, uid, a.shopName, a.address ?? null);
    audit(uid, "REGISTER_SHOPKEEPER", sid);
    return { userId: uid, shopId: sid };
  });
}
export async function verifyLogin(phone: string, password: string) {
  const u = one("SELECT id,role,password_hash FROM users WHERE phone=?", phone);
  const ok = await bcrypt.compare(password, u?.password_hash ?? "$2a$12$invalidinvalidinvalidinvalidinvalidinvalidinvalidinvalidi"); // constant-ish time
  return u && ok ? { id: u.id as string, role: u.role as string } : null;
}
export const shopOf = (userId: string) => one("SELECT id,name,currency FROM shops WHERE owner_id=?", userId) as { id: string; name: string; currency: string } | undefined;

export function createCustomer(shopId: string, actor: string, name: string, phone: string) {
  return tx(() => {
    if (one("SELECT 1 FROM customers WHERE shop_id=? AND phone=?", shopId, phone)) throw new DomainError("You already have a customer with this phone number");
    const id = randomUUID();
    db.prepare("INSERT INTO customers(id,shop_id,name,phone,invite_code) VALUES(?,?,?,?,?)").run(id, shopId, name, phone, randomBytes(4).toString("hex").toUpperCase());
    audit(actor, "CREATE_CUSTOMER", id);
    return id;
  });
}
// Balance rule: credit sales - confirmed repayments + adjustments; reversed/failed/pending excluded.
const LIVE = `shop_id=? AND customer_id=? AND status='CONFIRMED' AND type!='REVERSAL' AND id NOT IN (SELECT related_id FROM ledger WHERE type='REVERSAL' AND status='CONFIRMED' AND related_id IS NOT NULL)`;
export const balance = (shopId: string, customerId: string): number =>
  one(`SELECT COALESCE(SUM(CASE type WHEN 'CREDIT_SALE' THEN amount WHEN 'REPAYMENT' THEN -amount ELSE amount END),0) b FROM ledger WHERE ${LIVE}`, shopId, customerId)!.b;

export function listCustomers(shopId: string, search = "") {
  const like = `%${search.replace(/[%_]/g, "")}%`;
  return q("SELECT id,name,phone,active FROM customers WHERE shop_id=? AND (name LIKE ? OR phone LIKE ?) ORDER BY name", shopId, like, like)
    .map(c => ({ id: c.id as string, name: c.name as string, phone: c.phone as string, active: c.active as number, balance: balance(shopId, c.id) }));
}
// Always scoped by shop: another shop's customer id returns undefined (no IDOR).
export const getCustomer = (shopId: string, id: string) => one("SELECT id,name,phone,active,invite_code,user_id FROM customers WHERE shop_id=? AND id=?", shopId, id);
export const history = (shopId: string, customerId: string) =>
  q("SELECT id,reference,type,status,amount,description,quantity,unit_price,due_date,note,related_id,created_at FROM ledger WHERE shop_id=? AND customer_id=? ORDER BY created_at DESC, rowid DESC", shopId, customerId);

export function recordSale(a: { shopId: string; customerId: string; actor: string; description: string; quantity: number; unitPrice: number; dueDate?: string; note?: string; key: string }) {
  return tx(() => {
    const dup = one("SELECT id,reference,amount FROM ledger WHERE shop_id=? AND idempotency_key=?", a.shopId, a.key);
    if (dup) return { ...dup, duplicate: true } as Row;
    const c = getCustomer(a.shopId, a.customerId);
    if (!c || !c.active) throw new DomainError("Customer not found or inactive");
    const amount = a.quantity * a.unitPrice;
    if (!Number.isSafeInteger(amount) || amount <= 0) throw new DomainError("Invalid amount");
    const id = randomUUID(), reference = "KW-" + randomBytes(4).toString("hex").toUpperCase();
    db.prepare("INSERT INTO ledger(id,reference,shop_id,customer_id,type,amount,description,quantity,unit_price,due_date,note,idempotency_key,created_by) VALUES(?,?,?,?,'CREDIT_SALE',?,?,?,?,?,?,?,?)")
      .run(id, reference, a.shopId, a.customerId, amount, a.description, a.quantity, a.unitPrice, a.dueDate ?? null, a.note ?? null, a.key, a.actor);
    audit(a.actor, "CREDIT_SALE", id); if (settingsOf(a.shopId).sms_new_sale) queueSms(a.shopId, a.customerId, "NEW_SALE", "sale:" + id);
    return { id, reference, amount, duplicate: false };
  });
}

export function recordRepayment(a: { shopId: string; customerId: string; actor: string; amount: number; method: "CASH"; key: string }) {
  return tx(() => {
    const dup = one("SELECT id,reference,amount FROM ledger WHERE shop_id=? AND idempotency_key=?", a.shopId, a.key);
    if (dup) return { ...dup, duplicate: true } as Row;
    const c = getCustomer(a.shopId, a.customerId);
    if (!c || !c.active) throw new DomainError("Customer not found or inactive");
    if (!Number.isSafeInteger(a.amount) || a.amount <= 0) throw new DomainError("Invalid repayment amount");
    const bal = balance(a.shopId, a.customerId);
    if (a.amount > bal) throw new DomainError(`Repayment is more than the balance owed (${bal} RWF)`);
    const id = randomUUID(), reference = "KW-" + randomBytes(4).toString("hex").toUpperCase();
    db.prepare("INSERT INTO ledger(id,reference,shop_id,customer_id,type,amount,description,idempotency_key,created_by) VALUES(?,?,?,?,'REPAYMENT',?,?,?,?)")
      .run(id, reference, a.shopId, a.customerId, a.amount, `${a.method} repayment`, a.key, a.actor);
    audit(a.actor, "REPAYMENT", id); queueSms(a.shopId, a.customerId, "REPAYMENT", "repay:" + id);
    return { id, reference, amount: a.amount, duplicate: false };
  });
}
/** Corrections never delete: append a REVERSAL entry linked to the original, with a mandatory reason. */
export function reverseEntry(a: { shopId: string; entryId: string; actor: string; reason: string }) {
  return tx(() => {
    const o = one("SELECT id,customer_id,type,amount,status FROM ledger WHERE shop_id=? AND id=?", a.shopId, a.entryId);
    if (!o || o.status !== "CONFIRMED" || !["CREDIT_SALE", "REPAYMENT"].includes(o.type)) throw new DomainError("This transaction cannot be reversed");
    if (one("SELECT 1 FROM ledger WHERE related_id=? AND type='REVERSAL' AND status='CONFIRMED'", o.id)) throw new DomainError("Already reversed");
    if (o.type === "CREDIT_SALE" && balance(a.shopId, o.customer_id) - o.amount < 0) throw new DomainError("Reverse the related repayments first, so the balance does not go below zero");
    const id = randomUUID(), reference = "KW-" + randomBytes(4).toString("hex").toUpperCase();
    db.prepare("INSERT INTO ledger(id,reference,shop_id,customer_id,type,amount,description,related_id,note,created_by) VALUES(?,?,?,?,'REVERSAL',?,?,?,?,?)")
      .run(id, reference, a.shopId, o.customer_id, o.amount, "Reversal", o.id, a.reason, a.actor);
    audit(a.actor, "REVERSAL", id);
    return { id, reference };
  });
}
/** Distinct totals: credit issued, repayments received, outstanding (repayments are never counted as sales). */
export function shopTotals(shopId: string) {
  const live = `shop_id=? AND status='CONFIRMED' AND type!='REVERSAL' AND id NOT IN (SELECT related_id FROM ledger WHERE type='REVERSAL' AND status='CONFIRMED' AND related_id IS NOT NULL)`;
  const sum = (t: string) => one(`SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE ${live} AND type=?`, shopId, t)!.s as number;
  const credit = sum("CREDIT_SALE"), repaid = sum("REPAYMENT");
  return { credit, repaid, outstanding: credit - repaid };
}

export async function registerCustomerUser(a: { name: string; phone: string; email?: string; password: string }) {
  const hash = await bcrypt.hash(a.password, 12);
  return tx(() => {
    if (one("SELECT 1 FROM users WHERE phone=?", a.phone)) throw new DomainError("This phone number is already registered");
    const uid = randomUUID();
    db.prepare("INSERT INTO users(id,role,name,phone,email,password_hash) VALUES(?,?,?,?,?,?)").run(uid, "CUSTOMER", a.name, a.phone, a.email ?? null, hash);
    audit(uid, "REGISTER_CUSTOMER", uid);
    return { userId: uid };
  });
}
/** Secure linking: needs the shop's one-time invite code AND the code must have been issued for this account's own phone number. */
export function linkByInvite(userId: string, code: string) {
  return tx(() => {
    const u = one("SELECT phone FROM users WHERE id=? AND role='CUSTOMER'", userId);
    const c = one("SELECT id,phone FROM customers WHERE invite_code=? AND user_id IS NULL AND active=1", code.trim().toUpperCase());
    if (!u || !c || c.phone !== u.phone) throw new DomainError("Invalid or already used invite code"); // same message for every failure
    db.prepare("UPDATE customers SET user_id=?, invite_code=NULL WHERE id=?").run(userId, c.id);
    audit(userId, "LINK_CUSTOMER", c.id);
    return c.id as string;
  });
}
export const customerAccounts = (userId: string) =>
  q("SELECT c.id,c.shop_id,s.name shop_name FROM customers c JOIN shops s ON s.id=c.shop_id WHERE c.user_id=? AND c.active=1 ORDER BY s.name", userId)
    .map(r => ({ id: r.id as string, shopName: r.shop_name as string, balance: balance(r.shop_id, r.id) }));
/** Ownership check: a customer can only open accounts linked to their own user id. */
export const customerAccount = (userId: string, customerId: string) =>
  one("SELECT c.id,c.shop_id,s.name shop_name FROM customers c JOIN shops s ON s.id=c.shop_id WHERE c.user_id=? AND c.id=?", userId, customerId) as { id: string; shop_id: string; shop_name: string } | undefined;

// ---- Payments (provider-agnostic). Only a verified SUCCESSFUL event with matching amount/currency creates a repayment. ----
import type { ProviderEvent } from "./payments/provider";
export const newPaymentRef = () => "KWP-" + randomBytes(5).toString("hex").toUpperCase();
export function createPaymentAttempt(a: { userId: string; customerId: string; amount: number; reference: string; provider: string; providerRef: string; ttlMs?: number }) {
  return tx(() => {
    const c = customerAccount(a.userId, a.customerId); if (!c) throw new DomainError("Account not found");
    if (!Number.isSafeInteger(a.amount) || a.amount <= 0) throw new DomainError("Invalid payment amount");
    const bal = balance(c.shop_id, a.customerId); if (a.amount > bal) throw new DomainError(`You owe ${bal} RWF at this shop, so you cannot pay more than that`);
    const id = randomUUID(), exp = new Date(Date.now() + (a.ttlMs ?? 15 * 60000)).toISOString();
    db.prepare("INSERT INTO payment_attempts(id,reference,shop_id,customer_id,initiated_by,amount,currency,status,provider,provider_ref,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)")
      .run(id, a.reference, c.shop_id, a.customerId, a.userId, a.amount, "RWF", "PENDING", a.provider, a.providerRef, exp);
    audit(a.userId, "PAYMENT_INITIATED", id); return a.reference;
  });
}
export function processProviderEvent(ev: ProviderEvent, provider: string) {
  return tx(() => {
    if (one("SELECT 1 FROM provider_events WHERE event_id=?", ev.eventId)) return "duplicate" as const;
    const log = (o: string) => db.prepare("INSERT INTO provider_events(event_id,provider,provider_ref,outcome) VALUES(?,?,?,?)").run(ev.eventId, provider, ev.providerRef, o);
    const a = one("SELECT * FROM payment_attempts WHERE provider=? AND provider_ref=?", provider, ev.providerRef);
    if (!a) { log("unknown_payment"); return "unknown_payment" as const; }
    const setStatus = (st: string, ledgerId?: string) => db.prepare("UPDATE payment_attempts SET status=?, ledger_id=COALESCE(?,ledger_id) WHERE id=?").run(st, ledgerId ?? null, a.id);
    if (a.status === "SUCCESSFUL") { log("ignored"); return "ignored" as const; }
    const open = a.status === "PENDING" || a.status === "EXPIRED"; // money may still arrive after our timeout
    if (ev.status === "PENDING") { log("pending"); return "pending" as const; }
    if (ev.status !== "SUCCESSFUL") { if (open) { setStatus(ev.status); if (ev.status === "FAILED") queueSms(a.shop_id, a.customer_id, "PAYMENT_FAILED", "payfail:" + a.id); } log(ev.status.toLowerCase()); return ev.status === "FAILED" ? "failed" as const : "cancelled" as const; }
    if (!open || ev.amount !== a.amount || ev.currency !== a.currency || a.amount > balance(a.shop_id, a.customer_id)) {
      setStatus("REVIEW"); audit("system", "PAYMENT_NEEDS_REVIEW", a.id); queueSms(a.shop_id, a.customer_id, "PAYMENT_REVIEW", "payreview:" + a.id); log("review"); return "review" as const; // never auto-confirm doubtful money
    }
    const id = randomUUID(), reference = "KW-" + randomBytes(4).toString("hex").toUpperCase();
    db.prepare("INSERT INTO ledger(id,reference,shop_id,customer_id,type,amount,description,idempotency_key,created_by) VALUES(?,?,?,?,'REPAYMENT',?,?,?,?)")
      .run(id, reference, a.shop_id, a.customer_id, a.amount, `MoMo repayment via ${provider} (${a.reference})${provider === "SANDBOX" ? " - SIMULATION" : ""}`, "pay:" + a.id, a.initiated_by);
    setStatus("SUCCESSFUL", id); audit("system", "PAYMENT_CONFIRMED", a.id); queueSms(a.shop_id, a.customer_id, "REPAYMENT", "repay:" + id); log("confirmed"); return "confirmed" as const;
  });
}
/** Timeout handling: stale pending attempts become EXPIRED (a real provider adapter should query status first). */
export const expireStale = () => db.prepare("UPDATE payment_attempts SET status='EXPIRED' WHERE status='PENDING' AND expires_at < ?").run(new Date().toISOString());
export const forceExpire = (ref: string) => { db.prepare("UPDATE payment_attempts SET expires_at='2000-01-01T00:00:00.000Z' WHERE reference=?").run(ref); expireStale(); };
export const attemptForUser = (userId: string, ref: string) =>
  one("SELECT p.*, s.name shop_name, l.reference receipt_ref FROM payment_attempts p JOIN customers c ON c.id=p.customer_id JOIN shops s ON s.id=p.shop_id LEFT JOIN ledger l ON l.id=p.ledger_id WHERE c.user_id=? AND p.reference=?", userId, ref);
export const attemptsFor = (userId: string, customerId: string) => { expireStale();
  return q("SELECT p.reference,p.amount,p.status,p.created_at FROM payment_attempts p JOIN customers c ON c.id=p.customer_id WHERE c.user_id=? AND p.customer_id=? ORDER BY p.created_at DESC, p.rowid DESC LIMIT 10", userId, customerId); };

// ---- SMS: queue, reminders, retries (provider-agnostic) ----
import { createHash } from "node:crypto";
import type { SmsProvider } from "./sms";
const fmt = (n: number) => new Intl.NumberFormat("en-RW").format(n) + " RWF";
export const settingsOf = (shopId: string) => (one("SELECT sms_new_sale,remind_days_before FROM shop_settings WHERE shop_id=?", shopId) ?? { sms_new_sale: 0, remind_days_before: 2 }) as { sms_new_sale: number; remind_days_before: number };
export const saveSettings = (shopId: string, newSale: boolean, days: number) => {
  if (!Number.isInteger(days) || days < 0 || days > 30) throw new DomainError("Reminder days must be between 0 and 30");
  db.prepare("INSERT INTO shop_settings(shop_id,sms_new_sale,remind_days_before) VALUES(?,?,?) ON CONFLICT(shop_id) DO UPDATE SET sms_new_sale=excluded.sms_new_sale, remind_days_before=excluded.remind_days_before").run(shopId, newSale ? 1 : 0, days); };
/** Idempotent: the unique event key means one message per event/schedule. Returns true if newly queued. */
function queueSms(shopId: string, customerId: string, kind: string, key: string): boolean {
  const c = one("SELECT c.name,c.phone,s.name shop FROM customers c JOIN shops s ON s.id=c.shop_id WHERE c.id=? AND c.shop_id=?", customerId, shopId); if (!c) return false;
  const bal = fmt(balance(shopId, customerId)), hi = `Hello ${c.name}, `;
  const body = { NEW_SALE: `${hi}a credit purchase was recorded at ${c.shop}. Your outstanding balance is ${bal}. Log in to Kwishyura to review.`,
    REPAYMENT: `${hi}we received your payment at ${c.shop}. Your outstanding balance is ${bal}.`,
    PAYMENT_FAILED: `${hi}your payment at ${c.shop} was not completed. No money was taken. Please try again.`,
    PAYMENT_REVIEW: `${hi}your payment at ${c.shop} could not be confirmed yet and is being checked. Please contact the shop.`,
    UPCOMING: `${hi}your Kwishyura account has an outstanding balance of ${bal}. A repayment is due soon. Please log in to review your account and repayment options.`,
    OVERDUE: `${hi}your Kwishyura account has an outstanding balance of ${bal}. A repayment is overdue. Please log in to review your account and repayment options.`,
  }[kind]; if (!body) return false;
  return db.prepare("INSERT OR IGNORE INTO sms_notifications(id,shop_id,customer_id,kind,event_key,to_phone,body,next_attempt_at) VALUES(?,?,?,?,?,?,?,?)")
    .run(randomUUID(), shopId, customerId, kind, key, c.phone, body, new Date().toISOString()).changes > 0;
}
export function debtsFor(shopId: string, customerId: string) {
  const rows = q(`SELECT id,type,amount,due_date FROM ledger WHERE ${LIVE} ORDER BY created_at, rowid`, shopId, customerId);
  let paid = rows.filter(r => r.type === "REPAYMENT").reduce((s, r) => s + r.amount, 0);
  return rows.filter(r => r.type === "CREDIT_SALE").map(r => { const applied = Math.min(paid, r.amount); paid -= applied; return { id: r.id as string, remaining: r.amount - applied, dueDate: r.due_date as string | null }; });
}
const dueEnd = (d: string) => Date.parse(d + "T23:59:59.999Z"); // due dates are treated as UTC calendar days
export function scheduleReminders(now = new Date()) {
  let queued = 0;
  for (const c of q("SELECT id,shop_id FROM customers WHERE active=1")) {
    const days = settingsOf(c.shop_id).remind_days_before;
    for (const d of debtsFor(c.shop_id, c.id)) {
      if (d.remaining <= 0 || !d.dueDate) continue;
      const end = dueEnd(d.dueDate), t = +now;
      if (t > end) { if (queueSms(c.shop_id, c.id, "OVERDUE", `overdue:${d.id}:${Math.floor((t - end) / (7 * 864e5))}`)) queued++; } // at most weekly
      else if (end - t <= days * 864e5) { if (queueSms(c.shop_id, c.id, "UPCOMING", `upcoming:${d.id}`)) queued++; }
    }
  }
  return queued;
}
export async function processSmsQueue(p: SmsProvider, now = new Date()) {
  const due = q("SELECT id,to_phone,body,attempts FROM sms_notifications WHERE status='QUEUED' AND next_attempt_at<=? ORDER BY created_at", now.toISOString()); let sent = 0;
  for (const m of due) {
    try { await p.send({ to: m.to_phone, body: m.body });
      db.prepare("UPDATE sms_notifications SET status='SENT', provider=?, sent_at=?, attempts=attempts+1, error=NULL WHERE id=?").run(p.name, now.toISOString(), m.id); sent++;
    } catch (e) { const n = m.attempts + 1; // exponential backoff: 2, 4, 8, 16 minutes; FAILED after 5 attempts
      db.prepare("UPDATE sms_notifications SET attempts=?, status=?, next_attempt_at=?, error=? WHERE id=?").run(n, n >= 5 ? "FAILED" : "QUEUED", new Date(+now + 2 ** n * 60000).toISOString(), String((e as Error).message).slice(0, 200), m.id); }
  }
  return sent;
}
export const listSms = (shopId: string) => q("SELECT n.kind,n.status,n.attempts,n.provider,n.created_at,n.error,c.name FROM sms_notifications n LEFT JOIN customers c ON c.id=n.customer_id WHERE n.shop_id=? ORDER BY n.created_at DESC, n.rowid DESC LIMIT 50", shopId);
export function shopOverdue(shopId: string, now = new Date()) {
  let total = 0; for (const c of q("SELECT id FROM customers WHERE shop_id=? AND active=1", shopId)) for (const d of debtsFor(shopId, c.id)) if (d.remaining > 0 && d.dueDate && +now > dueEnd(d.dueDate)) total += d.remaining; return total;
}
// ---- Disputes ----
export function createDispute(userId: string, customerId: string, ledgerId: string, message: string) {
  return tx(() => { const c = customerAccount(userId, customerId); if (!c) throw new DomainError("Account not found");
    if (!one("SELECT 1 FROM ledger WHERE id=? AND customer_id=? AND shop_id=?", ledgerId, customerId, c.shop_id)) throw new DomainError("Transaction not found");
    if (message.trim().length < 5) throw new DomainError("Please describe the problem (at least 5 characters)");
    const id = randomUUID(); db.prepare("INSERT INTO disputes(id,shop_id,customer_id,ledger_id,message) VALUES(?,?,?,?,?)").run(id, c.shop_id, customerId, ledgerId, message.trim()); audit(userId, "DISPUTE_OPENED", id); return id; });
}
export const disputesFor = (shopId: string, customerId: string) => q("SELECT d.id,d.message,d.status,d.response,d.created_at,l.reference FROM disputes d JOIN ledger l ON l.id=d.ledger_id WHERE d.shop_id=? AND d.customer_id=? ORDER BY d.created_at DESC, d.rowid DESC", shopId, customerId);
export const resolveDispute = (shopId: string, id: string, actor: string, response: string) => {
  if (response.trim().length < 3) throw new DomainError("Please write a response");
  if (!db.prepare("UPDATE disputes SET status='RESOLVED', response=? WHERE id=? AND shop_id=?").run(response.trim(), id, shopId).changes) throw new DomainError("Dispute not found"); audit(actor, "DISPUTE_RESOLVED", id); };
// ---- CSV export (spreadsheet-formula-safe) ----
export const csvCell = (v: unknown) => { let t = String(v ?? ""); if (/^[=+\-@\t\r]/.test(t)) t = "'" + t; return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t; };
export function csvForShop(shopId: string, from?: string, to?: string) {
  const rows = q("SELECT l.reference,l.created_at,c.name,l.type,l.status,l.amount,l.description,l.due_date FROM ledger l JOIN customers c ON c.id=l.customer_id WHERE l.shop_id=? AND substr(l.created_at,1,10)>=? AND substr(l.created_at,1,10)<=? ORDER BY l.created_at", shopId, from || "0000-01-01", to || "9999-12-31");
  return ["reference,date,customer,type,status,amount_rwf,description,due_date", ...rows.map(r => [r.reference, r.created_at, r.name, r.type, r.status, r.amount, r.description, r.due_date].map(csvCell).join(","))].join("\n");
}
// ---- Password reset (single-use, 30-minute token; only a hash is stored) ----
const sha = (t: string) => createHash("sha256").update(t).digest("hex");
export function requestPasswordReset(phone: string, appUrl: string) {
  const u = one("SELECT id FROM users WHERE phone=?", phone); if (!u) return; // caller shows the same message either way
  const token = randomBytes(24).toString("hex");
  db.prepare("INSERT INTO password_resets(token_hash,user_id,expires_at) VALUES(?,?,?)").run(sha(token), u.id, new Date(Date.now() + 30 * 60000).toISOString());
  db.prepare("INSERT INTO sms_notifications(id,kind,event_key,to_phone,body,next_attempt_at) VALUES(?,?,?,?,?,?)").run(randomUUID(), "PASSWORD_RESET", "reset:" + sha(token), phone, `Kwishyura password reset link (valid 30 minutes): ${appUrl}/reset/${token}. Ignore this if you did not ask for it.`, new Date().toISOString());
  audit(u.id, "PASSWORD_RESET_REQUESTED", u.id);
}
export async function resetPassword(token: string, password: string) {
  if (password.length < 8) throw new DomainError("Password must be at least 8 characters");
  const hash = await bcrypt.hash(password, 12);
  return tx(() => { const r = one("SELECT user_id FROM password_resets WHERE token_hash=? AND used=0 AND expires_at>?", sha(token), new Date().toISOString());
    if (!r) throw new DomainError("This reset link is invalid or has expired");
    db.prepare("UPDATE users SET password_hash=? WHERE id=?").run(hash, r.user_id); db.prepare("UPDATE password_resets SET used=1 WHERE token_hash=?").run(sha(token)); audit(r.user_id, "PASSWORD_RESET_DONE", r.user_id); });
}

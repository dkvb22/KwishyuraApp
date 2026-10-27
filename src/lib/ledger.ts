// Pure, auditable ledger rules. Amounts are integers (RWF has no minor unit). Entries are append-only.
export type EntryType = "CREDIT_SALE" | "REPAYMENT" | "REVERSAL" | "ADJUSTMENT";
export type EntryStatus = "CONFIRMED" | "PENDING" | "FAILED";
export interface Entry {
  id: string; reference: string; shopId: string; customerId: string; type: EntryType;
  status: EntryStatus; amount: number; // ADJUSTMENT may be negative; others > 0
  dueDate?: Date; relatedId?: string; idempotencyKey?: string; createdBy: string; createdAt: Date;
}
export class LedgerError extends Error {}
const isMoney = (n: number) => Number.isSafeInteger(n);

export class Ledger {
  entries: Entry[] = [];
  audit: { actor: string; action: string; entityId: string }[] = [];
  private seq = 0;

  private add(e: Omit<Entry, "id" | "reference" | "createdAt">, now = new Date()): Entry {
    if (e.idempotencyKey) {
      const dup = this.entries.find(x => x.shopId === e.shopId && x.idempotencyKey === e.idempotencyKey);
      if (dup) return dup; // safe retry: no duplicate entry
    }
    const n = ++this.seq;
    const entry: Entry = { ...e, id: `e${n}`, reference: `KW-${String(n).padStart(6, "0")}`, createdAt: now };
    this.entries.push(entry);
    this.audit.push({ actor: e.createdBy, action: `${e.type}:${e.status}`, entityId: entry.id });
    return entry;
  }
  private reversedIds() {
    return new Set(this.entries.filter(e => e.type === "REVERSAL" && e.status === "CONFIRMED").map(e => e.relatedId));
  }
  private live(shopId: string, customerId: string) {
    const rev = this.reversedIds();
    return this.entries.filter(e => e.shopId === shopId && e.customerId === customerId
      && e.status === "CONFIRMED" && e.type !== "REVERSAL" && !rev.has(e.id));
  }
  /** balance = credit sales - confirmed repayments + authorized adjustments (reversed/failed/pending excluded) */
  balance(shopId: string, customerId: string): number {
    return this.live(shopId, customerId).reduce((s, e) =>
      s + (e.type === "CREDIT_SALE" ? e.amount : e.type === "REPAYMENT" ? -e.amount : e.amount), 0);
  }
  recordCreditSale(a: { shopId: string; customerId: string; quantity: number; unitPrice: number; dueDate?: Date; by: string; idempotencyKey?: string }) {
    if (![a.quantity, a.unitPrice].every(isMoney) || a.quantity <= 0 || a.unitPrice <= 0) throw new LedgerError("Invalid quantity or price");
    return this.add({ shopId: a.shopId, customerId: a.customerId, type: "CREDIT_SALE", status: "CONFIRMED",
      amount: a.quantity * a.unitPrice, dueDate: a.dueDate, idempotencyKey: a.idempotencyKey, createdBy: a.by });
  }
  recordRepayment(a: { shopId: string; customerId: string; amount: number; by: string; idempotencyKey?: string; status?: EntryStatus }) {
    if (!isMoney(a.amount) || a.amount <= 0) throw new LedgerError("Invalid repayment amount");
    const status = a.status ?? "CONFIRMED";
    if (status === "CONFIRMED" && a.amount > this.balance(a.shopId, a.customerId)) throw new LedgerError("Repayment exceeds outstanding balance");
    return this.add({ shopId: a.shopId, customerId: a.customerId, type: "REPAYMENT", status, amount: a.amount,
      idempotencyKey: a.idempotencyKey, createdBy: a.by });
  }
  /** Corrections never delete: append a REVERSAL pointing at the original. */
  reverse(entryId: string, shopId: string, by: string) {
    const orig = this.entries.find(e => e.id === entryId && e.shopId === shopId);
    if (!orig || orig.type === "REVERSAL") throw new LedgerError("Entry not found");
    if (this.reversedIds().has(orig.id)) throw new LedgerError("Already reversed");
    return this.add({ shopId, customerId: orig.customerId, type: "REVERSAL", status: "CONFIRMED", amount: orig.amount, relatedId: orig.id, createdBy: by });
  }
  /** Policy shown to users: repayments are applied oldest-credit-first (FIFO). */
  debts(shopId: string, customerId: string, now = new Date()) {
    const live = this.live(shopId, customerId);
    let paid = live.filter(e => e.type === "REPAYMENT").reduce((s, e) => s + e.amount, 0);
    return live.filter(e => e.type === "CREDIT_SALE").sort((a, b) => +a.createdAt - +b.createdAt || a.id.localeCompare(b.id)).map(s => {
      const applied = Math.min(paid, s.amount); paid -= applied;
      const remaining = s.amount - applied;
      const state = remaining === 0 ? "Paid" : s.dueDate && s.dueDate < now ? "Overdue" : applied > 0 ? "PartiallyPaid" : "Active";
      return { id: s.id, reference: s.reference, amount: s.amount, remaining, state };
    });
  }
}

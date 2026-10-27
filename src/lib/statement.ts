// Shared by shopkeeper and customer views so both read the same figures.
export function buildStatement(rows: any[]) {
  const byId = new Map(rows.map(r => [r.id, r]));
  const reversed = new Set(rows.filter(r => r.type === "REVERSAL").map(r => r.related_id));
  const eff = (r: any): number => r.status !== "CONFIRMED" ? 0 : r.type === "CREDIT_SALE" ? r.amount : r.type === "REPAYMENT" ? -r.amount : -(eff(byId.get(r.related_id) ?? { status: "X" }));
  let run = 0;
  const lines = [...rows].reverse().map(r => ({ r, run: (run += eff(r)) })).reverse();
  return { lines, byId, reversed };
}

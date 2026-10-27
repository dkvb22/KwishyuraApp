import { notFound } from "next/navigation"; import { randomUUID } from "node:crypto";
import { requireShopkeeper } from "../../../../lib/session"; import { getCustomer, balance, history, disputesFor } from "../../../../lib/db"; import { addSale, addRepayment, reverse, answerDispute } from "../../../actions"; import { buildStatement } from "../../../../lib/statement"; import { Flash, rwf } from "../../../ui";
export default async function Customer({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { id } = await params; const { e, ok } = await searchParams; const { shop } = await requireShopkeeper();
  const c = getCustomer(shop.id, id); if (!c) notFound(); // scoped by shop: other shops' ids 404
  const ds = disputesFor(shop.id, id), bal = balance(shop.id, id), rows = history(shop.id, id), { lines: stmt, byId, reversed } = buildStatement(rows);
  return (<><p><a href="/dashboard">← Customers</a></p><h1>{c.name}</h1><p className="mut">{c.phone} · {c.user_id ? "Linked to a customer account" : `Invite code ${c.invite_code} (share it with the customer)`}</p><Flash e={e} ok={ok} />
    <div className="card"><div className="mut">Outstanding balance</div><div className="big">{rwf(bal)}</div>
      <p className="mut">Repayments are applied to the oldest credit first. Balance = credit sales − repayments, excluding reversed entries.</p></div>
    <div className="grid"><div className="card"><h2>Record a credit sale</h2><form action={addSale}><input type="hidden" name="customerId" value={id} /><input type="hidden" name="key" value={randomUUID()} />
      <label htmlFor="d">Item description</label><input id="d" name="description" required />
      <label htmlFor="qt">Quantity</label><input id="qt" name="quantity" type="number" min={1} step={1} defaultValue={1} required />
      <label htmlFor="u">Unit price (RWF)</label><input id="u" name="unitPrice" type="number" min={1} step={1} required />
      <label htmlFor="dd">Repayment due date (optional)</label><input id="dd" name="dueDate" type="date" />
      <label htmlFor="nt">Notes (optional)</label><textarea id="nt" name="note" rows={2} maxLength={300} />
      <p className="mut">The total is calculated by the server when you save.</p><button>Save credit sale</button></form></div>
    <div className="card"><h2>Record a cash repayment</h2>{bal <= 0 ? <p className="mut">Nothing is owed, so there is nothing to repay.</p> :
      <form action={addRepayment}><input type="hidden" name="customerId" value={id} /><input type="hidden" name="key" value={randomUUID()} />
      <label htmlFor="ra">Amount received (RWF, up to {rwf(bal)})</label><input id="ra" name="amount" type="number" min={1} max={bal} step={1} required /><button>Save repayment</button></form>}</div></div>
    {ds.length > 0 && <div className="card"><h2>Customer questions</h2>{ds.map(d => <div key={d.id}><p><b>{d.reference}</b>: {d.message} ({d.status})</p>
      {d.status === "OPEN" ? <form action={answerDispute}><input type="hidden" name="customerId" value={id} /><input type="hidden" name="disputeId" value={d.id} />
        <label htmlFor={`a${d.id}`}>Your response</label><input id={`a${d.id}`} name="response" required minLength={3} /><button className="alt">Send response</button></form> : <p className="mut">Answered: {d.response}</p>}</div>)}</div>}
    <div className="card"><h2>Account statement</h2>{rows.length === 0 ? <p className="mut">No transactions yet.</p> : <div className="scroll"><table><thead><tr><th>Date</th><th>Ref</th><th>Type</th><th>Details</th><th>Amount</th><th>Balance</th><th>Action</th></tr></thead><tbody>
      {stmt.map(({ r, run }) => <tr key={r.id}><td>{r.created_at}</td><td>{r.reference}</td><td>{r.type.replace("_", " ")}{reversed.has(r.id) ? " (reversed)" : ""}</td>
        <td>{r.type === "REVERSAL" ? `Reverses ${byId.get(r.related_id)?.reference ?? ""}: ${r.note ?? ""}` : r.description ?? "—"}</td><td>{rwf(r.amount)}</td><td>{rwf(run)}</td>
        <td>{["CREDIT_SALE", "REPAYMENT"].includes(r.type) && !reversed.has(r.id) && <details><summary>Reverse</summary>
          <form action={reverse}><input type="hidden" name="customerId" value={id} /><input type="hidden" name="entryId" value={r.id} />
          <label htmlFor={`rs${r.id}`}>Reason (required)</label><input id={`rs${r.id}`} name="reason" required minLength={3} />
          <p className="mut">This keeps the original and adds a reversal. It cannot be undone.</p><button>Confirm reversal</button></form></details>}</td></tr>)}</tbody></table></div>}</div></>);
}

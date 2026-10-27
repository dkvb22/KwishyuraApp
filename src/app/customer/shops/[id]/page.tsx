import { notFound } from "next/navigation";
import { requireCustomer } from "../../../../lib/session"; import { customerAccount, balance, history, attemptsFor, disputesFor } from "../../../../lib/db"; import { buildStatement } from "../../../../lib/statement"; import { startPayment, openDispute } from "../../../actions"; import { Flash, rwf } from "../../../ui";
export default async function Statement({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { id } = await params; const { e, ok } = await searchParams; const { userId } = await requireCustomer();
  const a = customerAccount(userId, id); if (!a) notFound(); // not yours => 404, whatever the id
  const ds = disputesFor(a.shop_id, id), bal = balance(a.shop_id, id), tries = attemptsFor(userId, id), rows = history(a.shop_id, id), { lines, byId, reversed } = buildStatement(rows);
  return (<><p><a href="/customer">← My accounts</a></p><h1>{a.shop_name}</h1><Flash e={e} ok={ok} />
    <div className="card"><div className="mut">I owe this shop</div><div className="big">{rwf(balance(a.shop_id, id))}</div>
      <p className="mut">Read-only. If something looks wrong, speak to the shopkeeper.</p></div>
    <div className="card"><h2>Pay with Mobile Money</h2>{bal <= 0 ? <p className="mut">You owe nothing here.</p> :
      <form action={startPayment}><input type="hidden" name="customerId" value={id} /><p>Paying to: <b>{a.shop_name}</b>. <b>Test mode:</b> payments here are simulations; no real money moves.</p>
      <label htmlFor="pa">Amount (RWF, up to {rwf(bal)})</label><input id="pa" name="amount" type="number" min={1} max={bal} step={1} required /><button>Start payment</button></form>}
      {tries.length > 0 && <><h3>Previous payment attempts</h3><ul>{tries.map(t => <li key={t.reference}><a href={`/customer/payments/${t.reference}`}>{t.reference}</a> · {rwf(t.amount)} · {t.status}</li>)}</ul></>}</div>
    {ds.length > 0 && <div className="card"><h2>My questions</h2><ul>{ds.map(d => <li key={d.id}>{d.reference}: {d.message} · <b>{d.status === "OPEN" ? "Waiting for the shop" : "Answered"}</b>{d.response && <> · Shop: {d.response}</>}</li>)}</ul></div>}
    <div className="card"><h2>Account statement</h2>{rows.length === 0 ? <p className="mut">No transactions yet.</p> : <div className="scroll"><table><thead><tr><th>Date</th><th>Ref</th><th>Type</th><th>Details</th><th>Amount</th><th>Balance</th><th>Question</th></tr></thead><tbody>
      {lines.map(({ r, run }) => <tr key={r.id}><td>{r.created_at}</td><td>{r.reference}</td><td>{r.type === "CREDIT_SALE" ? "Credit purchase" : r.type === "REPAYMENT" ? "Payment" : "Reversal"}{reversed.has(r.id) ? " (reversed)" : ""}</td>
        <td>{r.type === "REVERSAL" ? `Reverses ${byId.get(r.related_id)?.reference ?? ""}` : r.type === "CREDIT_SALE" ? `${r.description} × ${r.quantity} @ ${rwf(r.unit_price)}` : r.description}</td><td>{rwf(r.amount)}</td><td>{rwf(run)}</td><td>{["CREDIT_SALE", "REPAYMENT"].includes(r.type) && <details><summary>Ask a question</summary><form action={openDispute}><input type="hidden" name="customerId" value={id} /><input type="hidden" name="ledgerId" value={r.id} /><label htmlFor={`q${r.id}`}>What looks wrong?</label><input id={`q${r.id}`} name="message" required minLength={5} /><button>Send to shop</button></form></details>}</td></tr>)}</tbody></table></div>}</div></>);
}

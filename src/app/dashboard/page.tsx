import { requireShopkeeper } from "../../lib/session"; import { listCustomers, shopTotals, shopOverdue } from "../../lib/db"; import { addCustomer } from "../actions"; import { Flash, rwf } from "../ui";
export default async function Dashboard({ searchParams }: { searchParams: Promise<{ e?: string; ok?: string; q?: string }> }) {
  const { e, ok, q } = await searchParams; const { shop } = await requireShopkeeper();
  const all = listCustomers(shop.id), shown = q ? listCustomers(shop.id, q) : all;
  const t = shopTotals(shop.id), total = t.outstanding, owing = all.filter(c => c.balance > 0).length;
  return (<><h1>{shop.name}</h1><p><a href="/dashboard/sms">SMS reminders</a> · <a href="/dashboard/export">Download all transactions (CSV)</a></p><Flash e={e} ok={ok} />
    <div className="grid"><div className="card"><div className="mut">Total outstanding credit</div><div className="big">{rwf(total)}</div></div>
    <div className="card"><div className="mut">Total credit issued</div><div className="big">{rwf(t.credit)}</div></div>
    <div className="card"><div className="mut">Repayments received</div><div className="big">{rwf(t.repaid)}</div></div>
    <div className="card"><div className="mut">Overdue (past due date)</div><div className="big">{rwf(shopOverdue(shop.id))}</div></div>
    <div className="card"><div className="mut">Customers with a balance</div><div className="big">{owing}</div></div></div>
    <div className="card"><h2>Add a customer</h2><form action={addCustomer}>
      <label htmlFor="n">Name</label><input id="n" name="name" required /><label htmlFor="p">Phone number</label><input id="p" name="phone" type="tel" placeholder="+250788123456" required />
      <button>Add customer</button></form></div>
    <div className="card"><h2>Customers</h2><form method="get"><label htmlFor="q">Search by name or phone</label><input id="q" name="q" defaultValue={q} /><button className="alt">Search</button></form>
      {shown.length === 0 ? <p className="mut">No customers yet. Add your first customer above.</p> :
      <div className="scroll"><table><thead><tr><th>Name</th><th>Phone</th><th>Balance</th></tr></thead><tbody>
      {shown.map(c => <tr key={c.id}><td><a href={`/dashboard/customers/${c.id}`}>{c.name}</a></td><td>{c.phone}</td><td>{rwf(c.balance)}</td></tr>)}</tbody></table></div>}</div></>);
}

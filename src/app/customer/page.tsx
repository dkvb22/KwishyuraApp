import { requireCustomer } from "../../lib/session"; import { customerAccounts } from "../../lib/db"; import { linkShop } from "../actions"; import { Flash, rwf } from "../ui";
export default async function CustomerHome({ searchParams }: { searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { e, ok } = await searchParams; const { userId } = await requireCustomer(); const accts = customerAccounts(userId);
  return (<><h1>My accounts</h1><Flash e={e} ok={ok} />
    <div className="card"><div className="mut">Total I owe</div><div className="big">{rwf(accts.reduce((s, a) => s + a.balance, 0))}</div></div>
    <div className="card"><h2>Shops</h2>{accts.length === 0 ? <p className="mut">No shops linked yet. Enter the invite code from your shopkeeper below.</p> :
      <div className="scroll"><table><thead><tr><th>Shop</th><th>I owe</th></tr></thead><tbody>{accts.map(a => <tr key={a.id}><td><a href={`/customer/shops/${a.id}`}>{a.shopName}</a></td><td>{rwf(a.balance)}</td></tr>)}</tbody></table></div>}</div>
    <div className="card"><h2>Link a shop</h2><form action={linkShop}><label htmlFor="code">Invite code</label><input id="code" name="code" required autoComplete="off" />
      <p className="mut">Codes work once and only for the phone number you registered with.</p><button>Link shop</button></form></div></>);
}

import { requireShopkeeper } from "../../../lib/session"; import { settingsOf, listSms } from "../../../lib/db"; import { getSmsProvider } from "../../../lib/sms"; import { saveSms } from "../../actions"; import { Flash } from "../../ui";
export default async function Sms({ searchParams }: { searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { e, ok } = await searchParams; const { shop } = await requireShopkeeper(); const st = settingsOf(shop.id), log = listSms(shop.id), sim = getSmsProvider().isSimulation;
  return (<><p><a href="/dashboard">← Dashboard</a></p><h1>SMS reminders</h1><Flash e={e} ok={ok} />
    {sim && <div className="ok" role="status"><b>Development mode:</b> messages are written to the server log. No real SMS is sent.</div>}
    <div className="card"><h2>Preferences</h2><form action={saveSms}>
      <label htmlFor="days">Remind customers this many days before the due date</label><input id="days" name="days" type="number" min={0} max={30} defaultValue={st.remind_days_before} />
      <label><input type="checkbox" name="newSale" defaultChecked={!!st.sms_new_sale} style={{width:"auto"}} /> Send an SMS when a new credit sale is recorded</label>
      <p className="mut">Overdue reminders go out at most once a week. Repayment confirmations are always sent.</p><button>Save</button></form></div>
    <div className="card"><h2>Recent messages</h2>{log.length === 0 ? <p className="mut">No messages yet.</p> : <div className="scroll"><table><thead><tr><th>Date</th><th>Customer</th><th>Type</th><th>Status</th><th>Tries</th></tr></thead><tbody>
      {log.map((m, i) => <tr key={i}><td>{m.created_at}</td><td>{m.name ?? "—"}</td><td>{m.kind}</td><td>{m.status}{m.provider === "DEV_LOG" ? " (dev log, not sent)" : ""}{m.error ? `: ${m.error}` : ""}</td><td>{m.attempts}</td></tr>)}</tbody></table></div>}</div></>);
}

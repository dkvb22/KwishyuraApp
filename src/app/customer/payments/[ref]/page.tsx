import { notFound } from "next/navigation";
import { requireCustomer } from "../../../../lib/session"; import { attemptForUser, expireStale } from "../../../../lib/db"; import { getProvider } from "../../../../lib/payments/provider"; import { simulatePayment } from "../../../actions"; import { Flash, rwf } from "../../../ui";
const LABEL: Record<string, string> = { PENDING: "Pending: waiting for confirmation", SUCCESSFUL: "Successful: payment confirmed", FAILED: "Failed: no money was taken", CANCELLED: "Cancelled", EXPIRED: "Expired: no confirmation arrived in time", REVIEW: "Under review: the shop will check this payment" };
export default async function PaymentPage({ params, searchParams }: { params: Promise<{ ref: string }>; searchParams: Promise<{ e?: string }> }) {
  const { ref } = await params; const { e } = await searchParams; const { userId } = await requireCustomer(); expireStale();
  const a = attemptForUser(userId, ref) as any; if (!a) notFound();
  const sim = getProvider().isSimulation;
  return (<><p><a href={`/customer/shops/${a.customer_id}`}>← Back to {a.shop_name}</a></p><h1>Payment {a.reference}</h1><Flash e={e} />
    <div className="card"><p>Shop: <b>{a.shop_name}</b></p><p>Amount: <b>{rwf(a.amount)}</b></p><p role="status">Status: <b>{LABEL[a.status] ?? a.status}</b></p>
      {a.status === "SUCCESSFUL" && <p>Receipt: repayment {a.receipt_ref} recorded on your account.</p>}
      {sim && <p className="mut"><b>SIMULATION:</b> this is not a real Mobile Money transaction.</p>}</div>
    {sim && ["PENDING", "EXPIRED"].includes(a.status) && <div className="card"><h2>Test controls (simulation only)</h2>
      {[["success", "Approve payment"], ["fail", "Decline payment"], ["cancel", "Cancel payment"], ["pending", "Stay pending"], ["timeout", "Simulate timeout"]].map(([o, l]) =>
        <form key={o} action={simulatePayment} style={{display:"inline-block",marginRight:8}}><input type="hidden" name="ref" value={ref} /><input type="hidden" name="outcome" value={o} /><button className="alt">{l}</button></form>)}</div>}</>);
}

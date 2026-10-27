import { doReset } from "../../actions"; import { Flash } from "../../ui";
export default async function Reset({ params, searchParams }: { params: Promise<{ token: string }>; searchParams: Promise<{ e?: string }> }) {
  const { token } = await params; const { e } = await searchParams;
  return (<div className="card" style={{maxWidth:420,margin:"2rem auto"}}><h1>Choose a new password</h1><Flash e={e} /><form action={doReset}><input type="hidden" name="token" value={token} />
    <label htmlFor="pw">New password (8+ characters)</label><input id="pw" name="password" type="password" minLength={8} required autoComplete="new-password" /><button>Change password</button></form></div>);
}

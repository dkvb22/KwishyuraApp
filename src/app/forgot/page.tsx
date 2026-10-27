import { forgot } from "../actions"; import { Flash } from "../ui";
export default async function Forgot({ searchParams }: { searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { e, ok } = await searchParams;
  return (<div className="card" style={{maxWidth:420,margin:"2rem auto"}}><h1>Reset password</h1><Flash e={e} ok={ok} /><form action={forgot}>
    <label htmlFor="phone">Phone number</label><input id="phone" name="phone" type="tel" placeholder="+250788123456" required /><button>Send reset link</button></form><p><a href="/login">Back to login</a></p></div>);
}

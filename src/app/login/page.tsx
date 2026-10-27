import { login } from "../actions"; import { Flash } from "../ui";
export default async function Login({ searchParams }: { searchParams: Promise<{ e?: string; ok?: string }> }) {
  const { e, ok } = await searchParams;
  return (<div className="card" style={{maxWidth:420,margin:"2rem auto"}}><h1>Log in</h1><Flash e={e} ok={ok} />
    <form action={login}><label htmlFor="phone">Phone number</label><input id="phone" name="phone" type="tel" placeholder="+250788123456" required autoComplete="tel" />
    <label htmlFor="password">Password</label><input id="password" name="password" type="password" required autoComplete="current-password" />
    <button>Log in</button></form><p><a href="/forgot">Forgot password?</a></p><p>New shopkeeper? <a href="/register">Create your shop account</a> · Customer? <a href="/register/customer">Create a customer account</a></p></div>);
}

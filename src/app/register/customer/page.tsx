import { registerCustomer } from "../../actions"; import { Flash } from "../../ui";
export default async function RegisterCustomer({ searchParams }: { searchParams: Promise<{ e?: string }> }) {
  const { e } = await searchParams;
  return (<div className="card" style={{maxWidth:480,margin:"2rem auto"}}><h1>Customer registration</h1><Flash e={e} />
    <form action={registerCustomer}>
    <label htmlFor="name">Full name</label><input id="name" name="name" required />
    <label htmlFor="phone">Phone number (the same one your shopkeeper has)</label><input id="phone" name="phone" type="tel" placeholder="+250788123456" required />
    <label htmlFor="email">Email (optional)</label><input id="email" name="email" type="email" />
    <label htmlFor="password">Password (8+ characters)</label><input id="password" name="password" type="password" minLength={8} required autoComplete="new-password" />
    <button>Create account</button></form><p>After signing up you will link your shop with the invite code your shopkeeper gives you. <a href="/login">Log in</a></p></div>);
}

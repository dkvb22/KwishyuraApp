import { register } from "../actions"; import { Flash } from "../ui";
export default async function Register({ searchParams }: { searchParams: Promise<{ e?: string }> }) {
  const { e } = await searchParams;
  return (<div className="card" style={{maxWidth:480,margin:"2rem auto"}}><h1>Shopkeeper registration</h1><Flash e={e} />
    <form action={register}>
    <label htmlFor="name">Full name</label><input id="name" name="name" required />
    <label htmlFor="shopName">Shop name</label><input id="shopName" name="shopName" required />
    <label htmlFor="phone">Phone number</label><input id="phone" name="phone" type="tel" placeholder="+250788123456" required />
    <label htmlFor="email">Email (optional)</label><input id="email" name="email" type="email" />
    <label htmlFor="address">Shop address (optional)</label><input id="address" name="address" />
    <label htmlFor="password">Password (8+ characters)</label><input id="password" name="password" type="password" minLength={8} required autoComplete="new-password" />
    <button>Create account</button></form><p>Already registered? <a href="/login">Log in</a></p></div>);
}

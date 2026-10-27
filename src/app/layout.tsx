import "./globals.css";
import { getSession } from "../lib/session";
import { logout } from "./actions";
export const metadata = { title: "kwishyura — Trust in Every Transaction." };
export default async function Root({ children }: { children: React.ReactNode }) {
  const s = await getSession();
  return (<html lang="en"><body>
    <header><div><b>kwishyura</b><small>Trust in Every Transaction.</small></div>{s && <form action={logout}><button style={{marginTop:0}} className="alt">Log out</button></form>}</header>
    <main>{children}</main></body></html>);
}

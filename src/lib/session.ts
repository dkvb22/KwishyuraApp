import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { shopOf } from "./db";
const key = () => { const s = process.env.AUTH_SECRET; if (!s || s.length < 32) throw new Error("AUTH_SECRET must be set (32+ chars)"); return new TextEncoder().encode(s); };
export async function createSession(userId: string, role: string) {
  const jwt = await new SignJWT({ role }).setProtectedHeader({ alg: "HS256" }).setSubject(userId).setExpirationTime("7d").sign(key());
  (await cookies()).set("kw_session", jwt, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 604800 });
}
export const destroySession = async () => (await cookies()).delete("kw_session");
export async function getSession() {
  const t = (await cookies()).get("kw_session")?.value; if (!t) return null;
  try { const { payload } = await jwtVerify(t, key()); return { userId: payload.sub as string, role: payload.role as string }; } catch { return null; }
}
/** Server-side guard: identity + role + owned shop. Never rely on hidden links. */
export async function requireShopkeeper() {
  const s = await getSession(); if (!s) redirect("/login");
  if (s.role !== "SHOPKEEPER") redirect("/login");
  const shop = shopOf(s.userId); if (!shop) redirect("/login");
  return { userId: s.userId, shop };
}
export async function requireCustomer() {
  const s = await getSession(); if (!s || s.role !== "CUSTOMER") redirect("/login");
  return { userId: s.userId };
}

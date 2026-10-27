export const rwf = (n: number) => `${new Intl.NumberFormat("en-RW").format(n)} RWF`;
export function Flash({ e, ok }: { e?: string; ok?: string }) {
  return <>{e && <div className="err" role="alert">{e}</div>}{ok && <div className="ok" role="status">{ok}</div>}</>;
}

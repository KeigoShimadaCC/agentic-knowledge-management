export function objectRoute(kind: string, id: string): string {
  if (kind === "page") return `/pages/${id}`;
  if (kind === "source") return `/sources/${id}`;
  if (kind === "chat") return `/app/chats/${id}`;
  if (kind === "asset") return "/app/assets";
  if (kind === "claim" || kind === "task") return "/app";
  return "/app";
}

export function objectKindLabel(kind: string): string {
  return kind.charAt(0).toUpperCase() + kind.slice(1);
}

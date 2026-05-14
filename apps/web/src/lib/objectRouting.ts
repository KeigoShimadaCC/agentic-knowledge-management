export function objectRoute(kind: string, id: string): string {
  if (kind === "page") return `/pages/${id}`;
  if (kind === "source") return `/sources/${id}`;
  return `/assets/${id}`;
}

export function objectKindLabel(kind: string): string {
  return kind.charAt(0).toUpperCase() + kind.slice(1);
}

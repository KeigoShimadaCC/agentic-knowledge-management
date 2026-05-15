export function objectRoute(kind: string, id: string): string {
  if (kind === "page") return `/app/pages/${id}`;
  if (kind === "source") return `/app/sources/${id}`;
  if (kind === "chat") return `/app/chats/${id}`;
  if (kind === "asset") return "/app/assets";
  if (kind === "project") return `/app/projects/${id}`;
  if (kind === "resume_bullet_set" || kind === "interview_story") return "/app/projects";
  if (kind === "claim" || kind === "task") return "/app";
  return "/app";
}

export function objectKindLabel(kind: string): string {
  return kind.charAt(0).toUpperCase() + kind.slice(1);
}

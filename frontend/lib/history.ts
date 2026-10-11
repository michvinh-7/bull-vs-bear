/** A debate id from what was pasted: the id itself, or any /debate/… or /brief/… link. */
export function idFrom(text: string): string {
  const t = text.trim().replace(/[?#].*$/, "").replace(/\/+$/, "");
  return t.split("/").pop() ?? "";
}

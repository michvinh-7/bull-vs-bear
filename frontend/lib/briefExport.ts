import { DISCLAIMER, type Claim, type Debate, type Label, type Speaker } from "./types";

/** Claim counts across the analysts' lines (the moderator's questions carry no claims worth scoring). */
export function claimCounts(debate: Pick<Debate, "lines">): Record<Exclude<Label, "pending">, number> & { total: number } {
  const claims = debate.lines.filter((l) => l.speaker !== "moderator").flatMap((l) => l.claims);
  const n = (label: Label) => claims.filter((c) => c.label === label).length;
  return { total: claims.length, verified: n("verified"), contested: n("contested"), unsupported: n("unsupported") };
}

/**
 * Links worth keeping in a pasted document. News sources found by Gemini search point at
 * Google's grounding redirects, which are long and stop working after a while.
 */
export function linkable(url: string | undefined): url is string {
  if (!url) return false;
  try {
    const u = new URL(url);
    return (u.protocol === "https:" || u.protocol === "http:") && !u.hostname.endsWith("vertexaisearch.cloud.google.com");
  } catch {
    return false;
  }
}

const NAME: Record<Speaker, string> = { bull: "Bull", bear: "Bear", moderator: "Portfolio manager" };

/**
 * The committee brief as Markdown, for pasting into notes, a doc or a chat.
 * Each cited claim is listed with its label and source so the reader can check it.
 */
export function briefMarkdown(debate: Debate, url?: string): string {
  const brief = debate.brief;
  if (!brief) return "";
  const sheet = debate.fact_sheet;
  const claims = new Map<string, { claim: Claim; speaker: Speaker }>(
    debate.lines.flatMap((l) => l.claims.map((c) => [c.id, { claim: c, speaker: l.speaker }] as const)),
  );
  const source = (id: string | null) => (id ? sheet?.sources.find((s) => s.id === id) : undefined);
  // One entry per label and source, with a count when several claims share it.
  const cite = (ids: string[]) => {
    const seen = new Map<string, { text: string; n: number }>();
    for (const id of ids) {
      const f = claims.get(id);
      if (!f) continue;
      const s = source(f.claim.source_id);
      const where = s ? (linkable(s.url) ? `[${s.label}](${s.url})` : s.label) : "no source";
      const key = `${f.claim.label}|${where}`;
      const e = seen.get(key);
      if (e) e.n++;
      else seen.set(key, { text: `${f.claim.label}: ${where}`, n: 1 });
    }
    const parts = [...seen.values()].map((e) => (e.n > 1 ? `${e.n}× ${e.text}` : e.text));
    return parts.length ? ` _(${parts.join("; ")})_` : "";
  };

  const counts = claimCounts(debate);
  const out: string[] = [];
  out.push(`# Committee brief: ${sheet ? `${sheet.company} (${sheet.ticker})` : debate.ticker}`);
  out.push("");
  const meta = [sheet ? `Figures as of ${sheet.as_of}` : null, `${debate.lines.length} turns`].filter(Boolean).join(" · ");
  out.push(meta, "");
  out.push(
    `${counts.total} claims checked: ${counts.verified} verified, ${counts.contested} contested, ${counts.unsupported} unsupported.`,
  );

  out.push("", "## Where both sides agree", "");
  if (brief.agreed.length) for (const a of brief.agreed) out.push(`- ${a.text}${cite(a.claim_ids)}`);
  else out.push("The analysts didn’t agree on anything.");

  out.push("", "## Where they disagree", "");
  if (brief.disputed.length) {
    for (const d of brief.disputed) {
      out.push(`### ${d.topic}`, "");
      out.push(`- **Bull:** ${d.bull}`);
      out.push(`- **Bear:** ${d.bear}`);
      const c = cite(d.claim_ids);
      if (c) out.push(`- Sources:${c}`);
      out.push("");
    }
    out.pop();
  } else out.push("No open disagreements.");

  out.push("", "## Claims without support", "");
  if (brief.unsupported.length) for (const u of brief.unsupported) out.push(`- **${NAME[u.speaker]}:** “${u.text}”`);
  else out.push("Every claim cited a source.");

  out.push("", "## What to check next", "");
  brief.open_questions.forEach((q, i) => out.push(`${i + 1}. ${q.question} _Where to look: ${q.where_to_look}_`));

  out.push("", "---", "");
  out.push(`_${DISCLAIMER}_`);
  if (url) out.push("", `_From Bull vs Bear, an AI credit committee: ${url}_`);
  return out.join("\n") + "\n";
}

/** LinkedIn's share dialog for a page; it reads the title and preview image from the page itself. */
export const linkedInShareUrl = (url: string) =>
  `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;

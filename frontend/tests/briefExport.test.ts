import { describe, expect, it } from "vitest";
import { briefMarkdown, claimCounts, linkable, linkedInShareUrl } from "@/lib/briefExport";
import { mockDebate } from "@/lib/mock";
import { DISCLAIMER, type Debate } from "@/lib/types";

describe("claimCounts", () => {
  it("counts analysts' claims by label and ignores the moderator", () => {
    const debate = {
      lines: [
        { speaker: "bull", claims: [{ label: "verified" }, { label: "contested" }] },
        { speaker: "moderator", claims: [{ label: "unsupported" }] },
        { speaker: "bear", claims: [{ label: "unsupported" }, { label: "pending" }] },
      ],
    } as unknown as Debate;
    expect(claimCounts(debate)).toEqual({ total: 4, verified: 1, contested: 1, unsupported: 1 });
  });
});

describe("briefMarkdown", () => {
  const md = briefMarkdown(mockDebate, "https://example.test/brief/mock");
  const brief = mockDebate.brief!;

  it("has a title with the company and ticker, and every section", () => {
    const sheet = mockDebate.fact_sheet!;
    expect(md.startsWith(`# Committee brief: ${sheet.company} (${sheet.ticker})\n`)).toBe(true);
    for (const h of ["## Where both sides agree", "## Where they disagree", "## Claims without support", "## What to check next"]) {
      expect(md).toContain(h);
    }
  });

  it("includes every point from the brief", () => {
    for (const a of brief.agreed) expect(md).toContain(a.text);
    for (const d of brief.disputed) {
      expect(md).toContain(`### ${d.topic}`);
      expect(md).toContain(`**Bull:** ${d.bull}`);
      expect(md).toContain(`**Bear:** ${d.bear}`);
    }
    for (const q of brief.open_questions) expect(md).toContain(q.question);
  });

  it("cites claims with their label and a linked source", () => {
    const cited = brief.agreed.flatMap((a) => a.claim_ids)[0];
    const claim = mockDebate.lines.flatMap((l) => l.claims).find((c) => c.id === cited)!;
    const source = mockDebate.fact_sheet!.sources.find((s) => s.id === claim.source_id)!;
    expect(md).toContain(`${claim.label}: [${source.label}](${source.url})`);
  });

  it("lists a repeated label and source once, with a count", async () => {
    const amc = (await import("../public/demo/AMC/debate.json")).default as unknown as Debate;
    const out = briefMarkdown(amc);
    expect(out).toMatch(/\d× verified: \[10-K · Financial statements\]\(https:\/\/www\.sec\.gov\//);
    expect(out).not.toContain("vertexaisearch");
  });

  it("ends with the disclaimer and the link back", () => {
    expect(md).toContain(`_${DISCLAIMER}_`);
    expect(md).toContain("https://example.test/brief/mock");
  });

  it("is empty when there's no brief yet", () => {
    expect(briefMarkdown({ ...mockDebate, brief: null })).toBe("");
  });
});

describe("linkable", () => {
  it("keeps normal links and drops grounding redirects and junk", () => {
    expect(linkable("https://www.sec.gov/Archives/x.htm")).toBe(true);
    expect(linkable("https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc")).toBe(false);
    expect(linkable("javascript:alert(1)")).toBe(false);
    expect(linkable("")).toBe(false);
  });
});

describe("linkedInShareUrl", () => {
  it("encodes the page url", () => {
    expect(linkedInShareUrl("https://x.test/brief/a b")).toBe(
      "https://www.linkedin.com/sharing/share-offsite/?url=https%3A%2F%2Fx.test%2Fbrief%2Fa%20b",
    );
  });
});

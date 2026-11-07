import type { Metadata } from "next";
import { claimCounts } from "@/lib/briefExport";
import { loadDebateOnServer } from "@/lib/serverDebate";

/**
 * Title and description for link previews (LinkedIn, Devpost, Slack, iMessage).
 * The preview image is opengraph-image.tsx next to this file; Next.js adds it to the tags.
 */
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const debate = await loadDebateOnServer(id);
  const sheet = debate?.fact_sheet;
  if (!debate?.brief) return { title: "Committee brief · Bull vs Bear" };

  const name = sheet ? `${sheet.company} (${sheet.ticker})` : debate.ticker;
  const c = claimCounts(debate);
  const topic = debate.brief.disputed[0]?.topic;
  const title = `Committee brief: ${name}`;
  const description = [
    `Two AI analysts debated ${sheet?.company ?? debate.ticker}’s debt; every claim was checked against the filings.`,
    `${c.verified} of ${c.total} claims verified.`,
    topic ? `Main disagreement: ${topic}.` : null,
  ]
    .filter(Boolean)
    .join(" ");

  return {
    title: `${title} · Bull vs Bear`,
    description,
    openGraph: { title, description, type: "article", siteName: "Bull vs Bear" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default function BriefLayout({ children }: { children: React.ReactNode }) {
  return children;
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getDebate } from "@/lib/api";
import { findSource } from "@/lib/format";
import { DISCLAIMER, type Debate } from "@/lib/types";

export default function BriefPage() {
  const { id } = useParams<{ id: string }>();
  // Loads the whole debate so brief items can link back to claims and their sources.
  const [debate, setDebate] = useState<Debate | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDebate(id).then(setDebate).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <main className="p-6 text-unsupported">{error}</main>;
  if (!debate) return <main className="p-6 text-neutral-400">Loading brief…</main>;
  if (!debate.brief) return <main className="p-6 text-neutral-400">The brief isn’t ready yet.</main>;
  const { brief, fact_sheet } = debate;

  // TODO(Person 3): make these chips open the same source drawer as the debate room.
  function Cites({ ids }: { ids: string[] }) {
    const labels = ids
      .map((id) => findSource(fact_sheet, debate!.lines.flatMap((l) => l.claims).find((c) => c.id === id)?.source_id ?? null)?.label)
      .filter(Boolean);
    if (!labels.length) return null;
    return <span className="ml-2 font-mono text-xs text-neutral-400">{Array.from(new Set(labels)).join(" · ")}</span>;
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
      <Link href="/" className="font-bold">
        Bull vs Bear
      </Link>
      <div>
        <h1 className="text-2xl font-bold">Committee brief</h1>
        {fact_sheet && (
          <p className="text-sm text-neutral-400">
            {fact_sheet.company} ({fact_sheet.ticker}) · figures as of {fact_sheet.as_of}
          </p>
        )}
      </div>

      <Section title="Both sides agree">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {brief.agreed.map((a, i) => (
            <li key={i}>
              {a.text}
              <Cites ids={a.claim_ids} />
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Disputed">
        {brief.disputed.map((d, i) => (
          <div key={i} className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-neutral-300">{d.topic}</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <p className="rounded-lg bg-bull-bg p-3 text-sm">
                <span className="font-semibold text-bull">Bull: </span>
                {d.bull}
              </p>
              <p className="rounded-lg bg-bear-bg p-3 text-sm">
                <span className="font-semibold text-bear">Bear: </span>
                {d.bear}
              </p>
            </div>
          </div>
        ))}
      </Section>

      <Section title="Unsupported claims">
        {brief.unsupported.length ? (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {brief.unsupported.map((u) => (
              <li key={u.claim_id}>
                <span className={u.speaker === "bull" ? "text-bull" : "text-bear"}>{u.speaker === "bull" ? "Bull" : "Bear"}: </span>
                {u.text}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-500">None.</p>
        )}
      </Section>

      <Section title="What to check next">
        <ul className="space-y-2 text-sm">
          {brief.open_questions.map((q, i) => (
            <li key={i}>
              {q.question}
              <div className="font-mono text-xs text-neutral-400">→ {q.where_to_look}</div>
            </li>
          ))}
        </ul>
      </Section>

      <p className="border-t border-line pt-4 text-sm text-neutral-400">{DISCLAIMER}</p>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 rounded-xl bg-panel p-4">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

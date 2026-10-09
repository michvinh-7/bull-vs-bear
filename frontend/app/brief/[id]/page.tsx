"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBrief } from "@/lib/api";
import { DISCLAIMER, type CommitteeBrief } from "@/lib/types";

export default function BriefPage({ params }: { params: { id: string } }) {
  const [brief, setBrief] = useState<CommitteeBrief | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBrief(params.id).then(setBrief).catch((e) => setError(e.message));
  }, [params.id]);

  if (error) return <main className="p-6 text-unsupported">{error}</main>;
  if (!brief) return <main className="p-6 text-neutral-400">Loading brief…</main>;

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
      <Link href="/" className="font-bold">
        Bull vs Bear
      </Link>
      <h1 className="text-2xl font-bold">Committee brief</h1>

      <Section title="Both sides agree">
        <List items={brief.agreed} />
      </Section>

      <Section title="Disputed">
        {brief.disputed.map((d, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-2">
            <p className="rounded-lg bg-bull-bg p-3 text-sm">
              <span className="font-semibold text-bull">Bull: </span>
              {d.bull}
            </p>
            <p className="rounded-lg bg-bear-bg p-3 text-sm">
              <span className="font-semibold text-bear">Bear: </span>
              {d.bear}
            </p>
          </div>
        ))}
      </Section>

      <Section title="Unsupported claims">
        <List items={brief.unsupported} />
      </Section>

      <Section title="What to look into next">
        <List items={brief.open_questions} />
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

function List({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-sm text-neutral-500">None.</p>;
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm">
      {items.map((x, i) => (
        <li key={i}>{x}</li>
      ))}
    </ul>
  );
}

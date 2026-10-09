"use client";

import Link from "next/link";
import { useState } from "react";
import { useDebate } from "@/lib/useDebate";
import type { Claim, LineMessage, Metric } from "@/lib/types";

const METRIC_LABELS: Record<string, (v: number) => [string, string]> = {
  leverage: (v) => ["Leverage", `${v}x`],
  interest_coverage: (v) => ["Interest coverage", `${v}x`],
  floating_rate_pct: (v) => ["Floating-rate debt", `${v}%`],
  next_maturity_year: (v) => ["Next big maturity", `${v}`],
  liquidity_usd: (v) => ["Liquidity", `$${Math.round(v / 1e6)}M`],
};

const SPEAKER_STYLE = {
  bull: { name: "Bull", box: "bg-bull-bg self-start", tag: "text-bull" },
  bear: { name: "Bear", box: "bg-bear-bg self-end", tag: "text-bear" },
  moderator: { name: "Portfolio manager", box: "bg-mod-bg self-center text-center", tag: "text-mod" },
};

export default function DebateRoom({ params }: { params: { id: string } }) {
  const { factSheet, lines, brief, status, error, interrupt } = useDebate(params.id);
  const [question, setQuestion] = useState("");
  const current = lines.at(-1)?.speaker;

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6">
      <header className="flex items-center justify-between">
        <Link href="/" className="font-bold">
          Bull vs Bear
        </Link>
        <span className="text-sm text-neutral-400">
          {factSheet ? `${factSheet.company} (${factSheet.ticker})` : "Loading…"} · {status}
        </span>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {factSheet?.metrics.map((m) => <MetricCard key={m.name} m={m} />)}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_2fr_1fr]">
        <SidePanel side="bull" active={current === "bull"} />

        <div className="flex min-h-[28rem] flex-col rounded-xl bg-panel p-4">
          <h2 className="mb-3 font-semibold">Committee floor</h2>
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
            {lines.map((l) => (
              <Line key={l.turn} line={l} />
            ))}
          </div>
          <form
            className="mt-3 flex gap-2 border-t border-line pt-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!question.trim()) return;
              interrupt(question.trim());
              setQuestion("");
            }}
          >
            <button className="rounded-full bg-unsupported px-4 py-2 text-sm font-semibold text-black">
              Interrupt
            </button>
            <input
              className="flex-1 rounded-full border border-line bg-bg px-4 py-2 text-sm outline-none"
              placeholder="Ask the committee a question…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </form>
        </div>

        <SidePanel side="bear" active={current === "bear"} />
      </section>

      {error && <p className="text-unsupported">{error}</p>}
      {brief && (
        <Link href={`/brief/${params.id}`} className="self-center rounded-lg bg-neutral-100 px-4 py-2 font-semibold text-black">
          Read the committee brief →
        </Link>
      )}
    </main>
  );
}

function MetricCard({ m }: { m: Metric }) {
  const [label, value] = METRIC_LABELS[m.name]?.(m.value) ?? [m.name, String(m.value)];
  return (
    <div className="rounded-xl bg-panel p-3" title={m.source}>
      <div className="text-xs text-neutral-400">{label}</div>
      <div className="font-mono text-xl">{value}</div>
    </div>
  );
}

function SidePanel({ side, active }: { side: "bull" | "bear"; active: boolean }) {
  // TODO(Person 3): thesis + key points (needs a field from the backend, or derive from lines).
  const s = SPEAKER_STYLE[side];
  return (
    <aside className={`rounded-xl bg-panel p-4 ${active ? (side === "bull" ? "ring-2 ring-bull" : "ring-2 ring-bear") : ""}`}>
      <div className={`font-semibold ${s.tag}`}>{s.name}</div>
      <div className="text-sm text-neutral-400">{active ? "Speaking now" : "Waiting"}</div>
    </aside>
  );
}

function Line({ line }: { line: LineMessage }) {
  const s = SPEAKER_STYLE[line.speaker];
  return (
    <div className={`max-w-[85%] rounded-lg p-3 ${s.box}`}>
      <div className={`text-xs font-semibold uppercase ${s.tag}`}>{s.name}</div>
      <p className="text-sm">{line.text}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {line.claims.map((c, i) => (
          <ClaimChip key={i} claim={c} />
        ))}
      </div>
    </div>
  );
}

const LABEL_COLOR = {
  verified: "border-verified text-verified",
  contested: "border-contested text-contested",
  unsupported: "border-unsupported text-unsupported",
  pending: "border-neutral-600 text-neutral-400",
};

function ClaimChip({ claim }: { claim: Claim }) {
  // TODO(Person 3): click opens a drawer with claim.passage and claim.source.
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className={`rounded border px-2 py-0.5 text-left font-mono text-xs ${LABEL_COLOR[claim.label]}`}
    >
      {claim.label} · {claim.source || "no source"}
      {open && claim.passage && <span className="mt-1 block font-sans text-neutral-300">“{claim.passage}”</span>}
    </button>
  );
}

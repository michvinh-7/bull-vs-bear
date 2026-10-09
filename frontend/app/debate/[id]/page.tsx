"use client";

import Link from "next/link";
import { useState } from "react";
import { useDebate } from "@/lib/useDebate";
import { findSource, formatMetric } from "@/lib/format";
import type { Claim, FactSheet, LineMessage, Metric, Position, Side, Speaker } from "@/lib/types";

const SPEAKER_STYLE = {
  bull: { name: "Bull", box: "bg-bull-bg self-start", tag: "text-bull", ring: "ring-bull" },
  bear: { name: "Bear", box: "bg-bear-bg self-end", tag: "text-bear", ring: "ring-bear" },
  moderator: { name: "Portfolio manager", box: "bg-mod-bg self-center text-center", tag: "text-mod", ring: "ring-mod" },
};

export default function DebateRoom({ params }: { params: { id: string } }) {
  const { factSheet, positions, lines, brief, thinking, maxTurns, status, error, interrupt } = useDebate(params.id);
  const [question, setQuestion] = useState("");
  const speaking: Speaker | undefined = thinking?.speaker ?? lines.at(-1)?.speaker;

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6">
      <header className="flex items-center justify-between">
        <Link href="/" className="font-bold">
          Bull vs Bear
        </Link>
        <span className="text-sm text-neutral-400">
          {factSheet ? `${factSheet.company} (${factSheet.ticker}) · ${factSheet.as_of}` : "Loading…"}
          {maxTurns && status === "live" && ` · Turn ${thinking?.turn ?? lines.length} of ${maxTurns}`}
          {status !== "live" && ` · ${status}`}
        </span>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {factSheet?.metrics.map((m) => <MetricCard key={m.name} m={m} />)}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_2fr_1fr]">
        <SidePanel side="bull" position={positions?.bull} lines={lines} active={speaking === "bull"} />

        <div className="flex min-h-[28rem] flex-col rounded-xl bg-panel p-4">
          <h2 className="mb-3 font-semibold">Committee floor</h2>
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
            {lines.map((l) => (
              <Line key={l.turn} line={l} sheet={factSheet} />
            ))}
            {thinking && (
              <p className={`text-sm italic ${SPEAKER_STYLE[thinking.speaker].tag}`}>
                {SPEAKER_STYLE[thinking.speaker].name} is thinking…
              </p>
            )}
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

        <SidePanel side="bear" position={positions?.bear} lines={lines} active={speaking === "bear"} />
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
  // TODO(Person 3): click to show formula + sources ("the AI never does math" proof).
  return (
    <div className="rounded-xl bg-panel p-3" title={m.formula}>
      <div className="text-xs text-neutral-400">{m.label}</div>
      <div className="font-mono text-xl">{formatMetric(m)}</div>
    </div>
  );
}

function SidePanel({ side, position, lines, active }: { side: Side; position?: Position; lines: LineMessage[]; active: boolean }) {
  const s = SPEAKER_STYLE[side];
  // Replaces "points scored": a count of this side's claims the fact-checker verified.
  const verified = lines.filter((l) => l.speaker === side).flatMap((l) => l.claims).filter((c) => c.label === "verified").length;
  return (
    <aside className={`flex flex-col gap-3 rounded-xl bg-panel p-4 ${active ? `ring-2 ${s.ring}` : ""}`}>
      <div>
        <div className={`font-semibold ${s.tag}`}>{s.name}</div>
        <div className="text-sm text-neutral-400">{active ? "Speaking now" : "Waiting"}</div>
      </div>
      {position && (
        <>
          <div className="text-xs uppercase text-neutral-500">Thesis</div>
          <p className="text-sm">{position.thesis}</p>
          <ul className="space-y-1 text-sm text-neutral-300">
            {position.points.map((p, i) => (
              <li key={i}>
                {side === "bull" ? "+" : "−"} {p.text}
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="mt-auto text-xs text-neutral-400">Verified claims · {verified}</div>
    </aside>
  );
}

function Line({ line, sheet }: { line: LineMessage; sheet: FactSheet | null }) {
  const s = SPEAKER_STYLE[line.speaker];
  return (
    <div className={`max-w-[85%] rounded-lg p-3 ${s.box}`}>
      <div className={`text-xs font-semibold uppercase ${s.tag}`}>{line.from_user ? "You asked" : s.name}</div>
      <p className="text-sm">{line.text}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {line.claims.map((c) => (
          <ClaimChip key={c.id} claim={c} sheet={sheet} />
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

function ClaimChip({ claim, sheet }: { claim: Claim; sheet: FactSheet | null }) {
  // TODO(Person 3): click opens a drawer with the source excerpt and a link to the filing.
  const [open, setOpen] = useState(false);
  const source = findSource(sheet, claim.source_id);
  return (
    <button
      onClick={() => setOpen(!open)}
      className={`rounded border px-2 py-0.5 text-left font-mono text-xs ${LABEL_COLOR[claim.label]}`}
    >
      {claim.label} · {source?.label ?? "no source"}
      {open && source && <span className="mt-1 block font-sans text-neutral-300">“{source.excerpt}”</span>}
    </button>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Mic, Pause, Play, Volume2, VolumeX } from "lucide-react";
import Bubble from "@/components/debate/Bubble";
import SidePanel, { type PanelStatus } from "@/components/debate/SidePanel";
import SourceSheet, { type SelectedClaim } from "@/components/debate/SourceSheet";
import { SPEAKER } from "@/components/debate/speakers";
import Logo from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatMetric } from "@/lib/format";
import type { Metric, Side } from "@/lib/types";
import { useDebate } from "@/lib/useDebate";
import { usePlayback } from "@/lib/usePlayback";

export default function DebateRoom() {
  const { id } = useParams<{ id: string }>();
  const { factSheet, positions, lines, brief, thinking, maxTurns, status, error, interrupt, pendingQuestion } = useDebate(id);
  const play = usePlayback(lines);
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<SelectedClaim | null>(null);
  const floorRef = useRef<HTMLDivElement>(null);

  // The question bubble stays up from "sent" until its moderator line is actually heard.
  const queuedQuestion = lines.slice(play.shown.length).find((l) => l.from_user)?.text;
  const waitingQuestion = pendingQuestion ?? queuedQuestion ?? null;
  const thinkingSpeaker = play.caughtUp && thinking ? thinking.speaker : null;

  function panelStatus(side: Side): PanelStatus {
    if (play.speaker === side) return "speaking";
    if (thinkingSpeaker === side) return "thinking";
    return "waiting";
  }

  // Keep the newest line in view, unless the user scrolled up to reread.
  useEffect(() => {
    const el = floorRef.current;
    if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 160) el.scrollTop = el.scrollHeight;
  }, [play.shown.length, play.progress, waitingQuestion, thinkingSpeaker]);

  const turn = play.current?.turn ?? play.shown.at(-1)?.turn;
  // Lines whose labels the audience has already seen (excludes the one being spoken).
  const heard = play.shown.filter((l) => l !== play.current);

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Logo />
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {status === "live" && !play.finished && <span className="size-2 animate-pulse rounded-full bg-unsupported" />}
          <span>
            {factSheet ? `${factSheet.company} (${factSheet.ticker}) · ${factSheet.as_of}` : "Loading…"}
            {maxTurns && turn && !play.finished ? ` · Turn ${turn} of ${maxTurns}` : ""}
            {play.finished && brief ? " · Debate finished" : ""}
          </span>
        </div>
      </header>

      {/* One swipeable row on phones, a grid from tablet up */}
      <section className="-mx-4 flex snap-x scroll-px-4 gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0 lg:grid-cols-5">
        {factSheet?.metrics.map((m) => <MetricCard key={m.name} m={m} />)}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_2fr_1fr]">
        <SidePanel side="bull" position={positions?.bull} heard={heard} status={panelStatus("bull")} paused={play.paused} />

        {/* On phones the floor comes first; side panels follow below it */}
        <Card className="relative order-first gap-0 p-0 lg:order-none">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div className="flex items-center gap-3">
              <h2 className="font-semibold">Committee floor</h2>
              {play.speaker && (
                <span className={`flex items-center gap-1.5 text-xs lg:hidden ${SPEAKER[play.speaker].text}`}>
                  <span className="size-1.5 animate-pulse rounded-full bg-current" />
                  {SPEAKER[play.speaker].name} speaking
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="icon" onClick={play.togglePause} aria-label={play.paused ? "Resume" : "Pause"}>
                {play.paused ? <Play /> : <Pause />}
              </Button>
              <Button variant="outline" size="icon" onClick={play.toggleMute} aria-label={play.muted ? "Unmute" : "Mute"}>
                {play.muted ? <VolumeX /> : <Volume2 />}
              </Button>
            </div>
          </div>

          <div ref={floorRef} className="flex h-[58vh] flex-col gap-3 overflow-y-auto p-4 sm:h-[26rem] lg:h-[30rem]">
            {play.shown.map((l) => (
              <Bubble
                key={l.turn}
                line={l}
                sheet={factSheet}
                active={play.current?.turn === l.turn}
                progress={play.progress}
                onClaim={(claim, line) => setSelected({ claim, speaker: line.speaker })}
              />
            ))}
            {waitingQuestion && (
              <div className="max-w-[88%] self-center rounded-lg border border-dashed border-mod/50 bg-mod-bg/60 p-3 text-center text-sm">
                <div className="text-xs font-semibold text-mod uppercase">You asked</div>
                {waitingQuestion}
                <div className="mt-1 text-xs text-muted-foreground">Sent. The committee takes it after this turn.</div>
              </div>
            )}
            {thinkingSpeaker && (
              <p className={`text-sm italic ${SPEAKER[thinkingSpeaker].text}`}>{SPEAKER[thinkingSpeaker].name} is thinking…</p>
            )}
            {play.shown.length === 0 && !play.blocked && (
              <p className="m-auto text-sm text-muted-foreground">The committee is taking its seats…</p>
            )}
          </div>

          {play.blocked && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-xl bg-background/80 backdrop-blur-sm">
              <Button size="lg" onClick={play.unblock}>
                <Play /> Play debate
              </Button>
              <p className="text-xs text-muted-foreground">Your browser needs a tap before it plays sound.</p>
            </div>
          )}

          <form
            className="flex gap-2 border-t p-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!question.trim() || waitingQuestion) return;
              interrupt(question.trim());
              setQuestion("");
            }}
          >
            <Button type="submit" className="rounded-full bg-unsupported text-black hover:bg-unsupported/90" disabled={!!waitingQuestion}>
              <Mic /> Interrupt
            </Button>
            <Input
              className="rounded-full"
              placeholder={waitingQuestion ? "Waiting for the committee…" : "Ask the committee a question…"}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={!!waitingQuestion}
            />
          </form>
        </Card>

        <SidePanel side="bear" position={positions?.bear} heard={heard} status={panelStatus("bear")} paused={play.paused} />
      </section>

      {error && <p className="text-sm text-unsupported">{error}</p>}
      {play.finished && brief && (
        <Button asChild size="lg" className="self-center">
          <Link href={`/brief/${id}`}>Read the committee brief →</Link>
        </Button>
      )}

      <SourceSheet selected={selected} sheet={factSheet} onClose={() => setSelected(null)} />
    </main>
  );
}

function MetricCard({ m }: { m: Metric }) {
  // TODO(Person 3): Tooltip with the formula + sources ("the AI never does math" proof).
  return (
    <Card className="min-w-36 shrink-0 snap-start gap-1 px-4 py-3 sm:min-w-0" title={m.formula}>
      <div className="text-xs text-muted-foreground">{m.label}</div>
      <div className="font-mono text-xl">{formatMetric(m)}</div>
    </Card>
  );
}

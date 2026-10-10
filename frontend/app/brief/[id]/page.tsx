"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FileSearch, Plus, RotateCcw } from "lucide-react";
import ClaimBadge from "@/components/ClaimBadge";
import Mascot from "@/components/debate/Mascot";
import SourceSheet, { type SelectedClaim } from "@/components/debate/SourceSheet";
import { SPEAKER } from "@/components/debate/speakers";
import Logo from "@/components/Logo";
import SettingsSheet from "@/components/SettingsSheet";
import { ThemeToggle } from "@/components/theme";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getDebate } from "@/lib/api";
import { unlockAudio } from "@/lib/audio";
import { findSource } from "@/lib/format";
import { DISCLAIMER, type Claim, type Debate, type Label, type Side, type Speaker, type Usage } from "@/lib/types";

/** A claim plus who said it, looked up from the debate transcript by claim id. */
type Found = { claim: Claim; speaker: Speaker };

export default function BriefPage() {
  const { id } = useParams<{ id: string }>();
  const [debate, setDebate] = useState<Debate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedClaim | null>(null);

  useEffect(() => {
    getDebate(id).then(setDebate).catch((e) => setError(e.message));
  }, [id]);

  if (error || (debate && !debate.brief)) {
    return (
      <Shell id={id}>
        <Card className="items-center p-10 text-center">
          <CardTitle>{error ? "We couldn’t load this brief" : "The brief isn’t ready yet"}</CardTitle>
          <CardDescription>{error ?? "The committee is still debating. Check back when it finishes."}</CardDescription>
          <Button asChild variant="outline">
            <Link href={`/debate/${id}`}>Back to the debate</Link>
          </Button>
        </Card>
      </Shell>
    );
  }
  if (!debate) {
    return (
      <Shell id={id}>
        <div className="flex flex-col gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-card" />
          ))}
        </div>
      </Shell>
    );
  }

  const brief = debate.brief!;
  const sheet = debate.fact_sheet;
  const byId = new Map<string, Found>(debate.lines.flatMap((l) => l.claims.map((c) => [c.id, { claim: c, speaker: l.speaker }] as const)));
  const find = (ids: string[]) => ids.map((i) => byId.get(i)).filter((f): f is Found => !!f);
  const open = (f: Found) => setSelected(f);

  const all = debate.lines.filter((l) => l.speaker !== "moderator").flatMap((l) => l.claims);
  const count = (label: Label) => all.filter((c) => c.label === label).length;

  return (
    <Shell id={id} usage={debate.usage}>
      {/* Title */}
      <section className="flex flex-col gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Committee brief</p>
          <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{sheet ? sheet.company : debate.ticker}</h1>
          {sheet && (
            <p className="text-sm text-muted-foreground">
              {sheet.ticker} · figures as of {sheet.as_of} · {debate.lines.length} turns
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {all.length} claims checked:
          {(["verified", "contested", "unsupported"] as const).map((l) => (
            <span key={l} className="flex items-center gap-1">
              <span className="font-mono text-foreground">{count(l)}</span>
              <ClaimBadge label={l} />
            </span>
          ))}
        </div>
      </section>

      {/* Agreed */}
      <Section title="Where both sides agree" description="Points neither analyst disputed.">
        {brief.agreed.length ? (
          <ul className="flex flex-col gap-3">
            {brief.agreed.map((a, i) => (
              <li key={i} className="flex flex-col gap-1.5">
                <span>{a.text}</span>
                <Citations found={find(a.claim_ids)} sheet={sheet} onOpen={open} />
              </li>
            ))}
          </ul>
        ) : (
          <Empty>The analysts didn’t agree on anything.</Empty>
        )}
      </Section>

      {/* Disputed */}
      <Section title="Where they disagree" description="Each side’s strongest version of the argument.">
        {brief.disputed.length ? (
          <div className="flex flex-col gap-6">
            {brief.disputed.map((d, i) => {
              const cited = find(d.claim_ids);
              return (
                <div key={i} className="flex flex-col gap-3">
                  <h3 className="font-semibold">{d.topic}</h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(["bull", "bear"] as const).map((side) => (
                      <SideTake
                        key={side}
                        side={side}
                        text={d[side]}
                        cited={cited.filter((f) => f.speaker === side)}
                        sheet={sheet}
                        onOpen={open}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty>No open disagreements.</Empty>
        )}
      </Section>

      {/* Unsupported */}
      <Section title="Claims without support" description="Said in the debate, but no source document backs them up.">
        {brief.unsupported.length ? (
          <ul className="flex flex-col gap-2">
            {brief.unsupported.map((u) => {
              const f = byId.get(u.claim_id);
              return (
                <li key={u.claim_id}>
                  <button
                    onClick={() => f && open(f)}
                    className="flex w-full items-start gap-3 rounded-lg bg-muted/50 p-3 text-left transition hover:bg-muted"
                  >
                    <Mascot side={u.speaker} size={28} />
                    <span className="flex flex-1 flex-col gap-1">
                      <span className={`text-xs font-semibold uppercase ${SPEAKER[u.speaker].text}`}>{SPEAKER[u.speaker].name}</span>
                      <span>“{u.text}”</span>
                    </span>
                    <ClaimBadge label="unsupported" className="mt-0.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <Empty>Every claim cited a source.</Empty>
        )}
      </Section>

      {/* Open questions */}
      <Section title="What to check next" description="Questions the debate raised but couldn’t settle, and where to look.">
        <ol className="flex flex-col gap-4">
          {brief.open_questions.map((q, i) => (
            <li key={i} className="flex gap-3">
              <span className="grid size-7 shrink-0 place-items-center rounded-full bg-muted font-mono text-xs">{i + 1}</span>
              <div className="flex flex-col gap-1">
                <span>{q.question}</span>
                <span className="flex items-start gap-1.5 font-mono text-xs text-muted-foreground">
                  <FileSearch className="mt-px size-3.5 shrink-0" />
                  {q.where_to_look}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      {/* Footer */}
      <section className="flex flex-col items-center gap-4 border-t pt-6 text-center">
        <p className="text-sm text-muted-foreground">{DISCLAIMER}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <ReplayButton id={id} />
          <Button asChild variant="outline">
            <Link href="/">
              <Plus /> Debate another company
            </Link>
          </Button>
        </div>
      </section>

      <SourceSheet selected={selected} sheet={sheet} onClose={() => setSelected(null)} />
    </Shell>
  );
}

function Shell({ id, usage, children }: { id: string; usage?: Usage | null; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-8 px-4 pt-5 pb-16">
      <header className="flex items-center justify-between gap-3">
        <Logo />
        <div className="flex items-center gap-1">
          <ReplayButton id={id} variant="ghost" />
          <SettingsSheet current={usage} />
          <ThemeToggle />
        </div>
      </header>
      {children}
    </main>
  );
}

/** Replays the saved debate. The click also unlocks audio for the replay. */
function ReplayButton({ id, variant = "default" }: { id: string; variant?: "default" | "ghost" }) {
  return (
    <Button asChild variant={variant} size={variant === "ghost" ? "sm" : "default"}>
      <Link href={`/debate/${id}?replay=1`} onClick={unlockAudio}>
        <RotateCcw /> Replay debate
      </Link>
    </Button>
  );
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-display text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="text-sm leading-relaxed">{children}</CardContent>
    </Card>
  );
}

function SideTake({
  side,
  text,
  cited,
  sheet,
  onOpen,
}: {
  side: Side;
  text: string;
  cited: Found[];
  sheet: Debate["fact_sheet"];
  onOpen: (f: Found) => void;
}) {
  const s = SPEAKER[side];
  return (
    <div className={`flex flex-col gap-2 rounded-lg p-3 ${s.bg}`}>
      <div className={`flex items-center gap-2 text-xs font-semibold uppercase ${s.text}`}>
        <Mascot side={side} size={24} />
        {s.name}
      </div>
      <p>{text}</p>
      <Citations found={cited} sheet={sheet} onOpen={onOpen} />
    </div>
  );
}

/** Clickable label chips; each opens the same source drawer as the debate room. */
function Citations({ found, sheet, onOpen }: { found: Found[]; sheet: Debate["fact_sheet"]; onOpen: (f: Found) => void }) {
  if (!found.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {found.map((f) => (
        <button key={f.claim.id} title={f.claim.text} onClick={() => onOpen(f)} className="rounded-sm focus-visible:ring-2 focus-visible:ring-ring">
          <ClaimBadge
            label={f.claim.label}
            source={findSource(sheet, f.claim.source_id)?.label ?? "no source"}
            className="cursor-pointer hover:brightness-125"
          />
        </button>
      ))}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-muted-foreground">{children}</p>;
}

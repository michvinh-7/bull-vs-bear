"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ArrowLeftRight, ArrowRight, Check, FileText } from "lucide-react";
import ClaimBadge from "@/components/ClaimBadge";
import MaturityWall from "@/components/MaturityWall";
import SiteHeader from "@/components/SiteHeader";
import { SPEAKER } from "@/components/debate/speakers";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getDebate, getHistory } from "@/lib/api";
import { claimCounts } from "@/lib/briefExport";
import { compareHref, compareMetrics, type MetricRow } from "@/lib/compare";
import { formatMetric } from "@/lib/format";
import { DISCLAIMER, type Debate, type DebateSummary, type Metric } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ComparePage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 pt-10 pb-16">
        <Suspense>
          <Compare />
        </Suspense>
      </main>
    </>
  );
}

function Compare() {
  const params = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");
  if (!a || !b || a === b) return <Picker first={a} />;
  return <Comparison key={`${a}|${b}`} a={a} b={b} />;
}

// ---- Choosing two debates ----

/** Shown when /compare is opened without two debates: pick them from History. */
function Picker({ first }: { first: string | null }) {
  const router = useRouter();
  const [rows, setRows] = useState<DebateSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>(first ? [first] : []);

  useEffect(() => {
    getHistory().then(setRows).catch((e) => setError(e.message));
  }, []);

  const toggle = (id: string) => {
    const next = picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id].slice(-2);
    setPicked(next);
    if (next.length === 2) router.push(compareHref(next[0], next[1]));
  };

  return (
    <>
      <section className="flex flex-col gap-2">
        <h1 className="font-display text-3xl font-bold tracking-tight">Compare two companies</h1>
        <p className="text-sm text-muted-foreground">
          Pick two finished debates to see their metrics, maturity walls and briefs side by side.
        </p>
      </section>
      {error && <p className="text-sm text-unsupported">{error}</p>}
      {!rows && !error && <div className="h-40 animate-pulse rounded-xl bg-card" />}
      {rows && rows.length < 2 && (
        <Card className="items-center p-8 text-center">
          <CardTitle>You need two finished debates</CardTitle>
          <CardDescription>Run another debate from the home page, then come back.</CardDescription>
          <Button asChild>
            <Link href="/">Start a debate</Link>
          </Button>
        </Card>
      )}
      {rows && rows.length >= 2 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {rows.map((r) => {
            const on = picked.includes(r.id);
            return (
              <li key={r.id}>
                <button
                  onClick={() => toggle(r.id)}
                  aria-pressed={on}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl border bg-card p-4 text-left transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden",
                    on && "border-foreground/40 bg-accent",
                  )}
                >
                  <span className={cn("grid size-5 shrink-0 place-items-center rounded-full border", on && "border-foreground bg-foreground text-background")}>
                    {on && <Check className="size-3.5" />}
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="flex items-center gap-2 font-medium">
                      <Badge variant="secondary" className="rounded-sm font-mono">{r.ticker}</Badge>
                      <span className="truncate">{r.company ?? r.ticker}</span>
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {r.as_of ? `figures as of ${r.as_of} · ` : ""}
                      {r.lines} lines{r.is_demo ? " · demo" : ""}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

// ---- The comparison ----

function Comparison({ a, b }: { a: string; b: string }) {
  const [debates, setDebates] = useState<[Debate, Debate] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDebate(a), getDebate(b)])
      .then(setDebates)
      .catch((e) => setError(e.message));
  }, [a, b]);

  if (error) {
    return (
      <Card className="items-center p-10 text-center">
        <CardTitle>We couldn’t load one of these debates</CardTitle>
        <CardDescription>{error}</CardDescription>
        <Button asChild variant="outline">
          <Link href="/compare">Pick again</Link>
        </Button>
      </Card>
    );
  }
  if (!debates) {
    return (
      <div className="flex flex-col gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-xl bg-card" />
        ))}
      </div>
    );
  }

  const [da, db] = debates;
  const rows = compareMetrics(da.fact_sheet, db.fact_sheet);

  return (
    <>
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-muted-foreground">Side by side</p>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              {da.ticker} <span className="text-muted-foreground">vs</span> {db.ticker}
            </h1>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href={compareHref(b, a)}>
                <ArrowLeftRight /> Swap
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href={`/compare?a=${encodeURIComponent(a)}`}>Change</Link>
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <CompanyCard id={a} debate={da} />
          <CompanyCard id={b} debate={db} />
        </div>
      </section>

      <MetricsTable rows={rows} a={da.ticker} b={db.ticker} />

      {(da.fact_sheet || db.fact_sheet) && (
        <section className="grid gap-4 lg:grid-cols-2">
          {[da, db].map((d) =>
            d.fact_sheet ? (
              <div key={d.id} className="flex flex-col gap-2">
                <h2 className="text-sm font-semibold">{d.ticker}</h2>
                <MaturityWall sheet={d.fact_sheet} className="h-full" />
              </div>
            ) : null,
          )}
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-semibold">What each committee concluded</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <BriefColumn id={a} debate={da} />
          <BriefColumn id={b} debate={db} />
        </div>
      </section>

      <p className="text-center text-sm text-muted-foreground">{DISCLAIMER}</p>
    </>
  );
}

function CompanyCard({ id, debate }: { id: string; debate: Debate }) {
  const sheet = debate.fact_sheet;
  const c = claimCounts(debate);
  return (
    <Card className="gap-2 p-4 sm:p-5">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="rounded-sm font-mono">{debate.ticker}</Badge>
        {sheet && <span className="text-xs text-muted-foreground">as of {sheet.as_of}</span>}
      </div>
      <div className="font-display text-lg leading-tight font-semibold sm:text-xl">{sheet?.company ?? debate.ticker}</div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <span>{c.total} claims:</span>
        <span className="flex items-center gap-1">
          <span className="font-mono text-foreground">{c.verified}</span>
          <ClaimBadge label="verified" />
        </span>
        {c.unsupported > 0 && (
          <span className="flex items-center gap-1">
            <span className="font-mono text-foreground">{c.unsupported}</span>
            <ClaimBadge label="unsupported" />
          </span>
        )}
      </div>
      <Link href={`/brief/${id}`} className="mt-1 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <FileText className="size-4" /> Full brief <ArrowRight className="size-3.5" />
      </Link>
    </Card>
  );
}

function MetricsTable({ rows, a, b }: { rows: MetricRow[]; a: string; b: string }) {
  if (!rows.length) return null;
  return (
    <Card className="gap-0 p-0">
      <CardHeader className="border-b py-4">
        <CardTitle className="font-display text-lg">Metrics</CardTitle>
        <CardDescription>
          Calculated by code from each 10-K. A check marks the stronger reading for a lender; dollar amounts aren’t marked,
          since company size differs.
        </CardDescription>
      </CardHeader>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-muted-foreground">
            <th className="px-4 py-2 text-left font-normal sm:px-6">Metric</th>
            <th className="px-4 py-2 text-right font-mono font-normal sm:px-6">{a}</th>
            <th className="px-4 py-2 text-right font-mono font-normal sm:px-6">{b}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name} className="border-b last:border-0">
              <td className="px-4 py-3 sm:px-6">
                {r.why ? (
                  <Tooltip>
                    <TooltipTrigger className="cursor-help text-left underline decoration-dotted underline-offset-4">{r.label}</TooltipTrigger>
                    <TooltipContent>{r.why}</TooltipContent>
                  </Tooltip>
                ) : (
                  r.label
                )}
              </td>
              <Cell m={r.a} stronger={r.stronger === "a"} />
              <Cell m={r.b} stronger={r.stronger === "b"} />
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Cell({ m, stronger }: { m?: Metric; stronger: boolean }) {
  return (
    <td className="px-4 py-3 text-right sm:px-6">
      <span className={cn("inline-flex items-center justify-end gap-1.5 font-mono", stronger && "font-semibold text-verified")}>
        {stronger && <Check className="size-3.5" aria-label="stronger" />}
        {m ? (
          <span title={m.formula || undefined}>{formatMetric(m)}</span>
        ) : (
          <span className="text-muted-foreground">–</span>
        )}
      </span>
    </td>
  );
}

function BriefColumn({ id, debate }: { id: string; debate: Debate }) {
  const brief = debate.brief;
  return (
    <Card className="gap-5 p-5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-display text-lg font-semibold">{debate.fact_sheet?.company ?? debate.ticker}</h3>
        <Link href={`/brief/${id}`} className="shrink-0 text-sm whitespace-nowrap text-muted-foreground hover:text-foreground">
          Brief →
        </Link>
      </div>
      {!brief ? (
        <p className="text-sm text-muted-foreground">This debate has no brief yet.</p>
      ) : (
        <>
          <Block title="Where they disagree">
            {brief.disputed.length ? (
              <div className="flex flex-col gap-4">
                {brief.disputed.map((d, i) => (
                  <div key={i} className="flex flex-col gap-1.5">
                    <div className="font-medium">{d.topic}</div>
                    {(["bull", "bear"] as const).map((side) => (
                      <p key={side} className="flex gap-2">
                        <span className={cn("w-9 shrink-0 text-xs font-semibold uppercase leading-5", SPEAKER[side].text)}>{SPEAKER[side].name}</span>
                        <span className="text-foreground/85">{d[side]}</span>
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">No open disagreements.</p>
            )}
          </Block>
          <Block title="Both sides agree">
            {brief.agreed.length ? (
              <ul className="list-disc space-y-1 pl-4">
                {brief.agreed.map((x, i) => (
                  <li key={i}>{x.text}</li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">Nothing agreed.</p>
            )}
          </Block>
          <Block title="What to check next">
            <ol className="list-decimal space-y-1 pl-4">
              {brief.open_questions.map((q, i) => (
                <li key={i}>{q.question}</li>
              ))}
            </ol>
          </Block>
        </>
      )}
    </Card>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 text-sm leading-relaxed">
      <div className="text-xs text-muted-foreground uppercase">{title}</div>
      {children}
    </div>
  );
}

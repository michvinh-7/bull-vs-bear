"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, FileText, Search } from "lucide-react";
import ClaimBadge from "@/components/ClaimBadge";
import { Badge } from "@/components/ui/badge";
import SiteHeader from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getHistory } from "@/lib/api";
import { idFrom } from "@/lib/history";
import { formatUsd } from "@/lib/settings";
import type { DebateSummary, Label } from "@/lib/types";

const MODEL_LABEL: Record<string, string> = {
  "gemini-3.6-flash": "Flash",
  "gemini-3.5-flash": "Flash",
  "gemini-3.5-flash-lite": "Flash-Lite",
  "gemini-3.1-pro-preview": "Pro",
};

function when(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function HistoryPage() {
  const router = useRouter();
  const [rows, setRows] = useState<DebateSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lookup, setLookup] = useState("");

  useEffect(() => {
    getHistory()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex max-w-4xl flex-col gap-8 px-4 pt-10 pb-16">
        <section className="flex flex-col gap-2">
          <h1 className="font-display text-3xl font-bold tracking-tight">Past debates</h1>
          <p className="text-sm text-muted-foreground">
            Every finished debate with a committee brief. Open one to read its brief and full transcript right away, or replay it.
          </p>
        </section>

        {/* Open any debate by its id (or a pasted link) */}
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const id = idFrom(lookup);
            if (id) router.push(`/brief/${id}`);
          }}
        >
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9 font-mono text-sm"
              placeholder="Debate ID or link, e.g. aac5836d5ccf"
              aria-label="Debate ID or link"
              autoComplete="off"
              value={lookup}
              onChange={(e) => setLookup(e.target.value)}
            />
          </div>
          <Button type="submit" variant="outline" disabled={!lookup.trim()}>
            Open
          </Button>
        </form>

        {error && (
          <Card className="items-center p-8 text-center">
            <CardTitle>We couldn’t load past debates</CardTitle>
            <CardDescription>{error}</CardDescription>
          </Card>
        )}

        {!rows && !error && (
          <div className="flex flex-col gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-card" />
            ))}
          </div>
        )}

        {rows && rows.length === 0 && (
          <Card className="items-center p-8 text-center">
            <CardTitle>No finished debates yet</CardTitle>
            <CardDescription>Start one from the home page; it shows up here when the committee finishes.</CardDescription>
            <Button asChild>
              <Link href="/">Start a debate</Link>
            </Button>
          </Card>
        )}

        {rows && rows.length > 0 && (
          <ul className="flex flex-col gap-3">
            {rows.map((r) => (
              <li key={r.id}>
                <Link href={`/brief/${r.id}`} className="group block rounded-xl focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden">
                  <Card className="gap-3 py-4 transition group-hover:ring-foreground/25">
                    <CardHeader className="gap-1">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 flex-col gap-1">
                          <CardTitle className="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary" className="rounded-sm font-mono">
                              {r.ticker}
                            </Badge>
                            <span className="truncate">{r.company ?? r.ticker}</span>
                            {r.is_demo && <Badge variant="outline">Demo</Badge>}
                          </CardTitle>
                          <CardDescription className="flex flex-wrap gap-x-3 gap-y-0.5">
                            {r.updated_at && <span>{when(r.updated_at)}</span>}
                            {r.as_of && <span>figures as of {r.as_of}</span>}
                            <span>{r.lines} lines</span>
                            {r.model && <span>{MODEL_LABEL[r.model] ?? r.model}</span>}
                            {r.cost_usd != null && <span className="font-mono">{formatUsd(r.cost_usd)}</span>}
                          </CardDescription>
                        </div>
                        <span className="flex shrink-0 items-center gap-1 text-sm text-muted-foreground transition group-hover:text-foreground">
                          <FileText className="size-4" />
                          <span className="hidden sm:inline">Brief</span>
                          <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-wrap gap-2">
                      {(["verified", "contested", "unsupported", "pending"] as Label[])
                        .filter((l) => r.labels[l])
                        .map((l) => (
                          <span key={l} className="flex items-center gap-1 text-xs">
                            <span className="font-mono">{r.labels[l]}</span>
                            <ClaimBadge label={l} />
                          </span>
                        ))}
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}

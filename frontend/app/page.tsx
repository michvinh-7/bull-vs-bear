"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import ClaimBadge from "@/components/ClaimBadge";
import Mascot from "@/components/debate/Mascot";
import Logo from "@/components/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { startDebate } from "@/lib/api";
import { unlockAudio } from "@/lib/audio";
import { getCompanies, MOCK_COMPANIES, type DemoCompany } from "@/lib/companies";
import type { Label } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [companies, setCompanies] = useState<DemoCompany[]>(MOCK_COMPANIES);
  const [starting, setStarting] = useState<string | null>(null);

  useEffect(() => {
    getCompanies().then(setCompanies);
  }, []);

  async function go(t: string) {
    if (!t.trim() || starting) return;
    unlockAudio(); // must run inside the click, before any await
    setStarting(t.trim().toUpperCase());
    try {
      const id = await startDebate(t.trim());
      router.push(`/debate/${id}`);
    } catch (e) {
      toast.error("Couldn’t start the debate", { description: (e as Error).message });
      setStarting(null);
    }
  }

  return (
    <div className="relative overflow-hidden">
      {/* Bull-blue and bear-orange glows behind the hero */}
      <div aria-hidden className="pointer-events-none absolute -top-40 -left-40 size-[32rem] rounded-full bg-bull/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -top-24 -right-40 size-[28rem] rounded-full bg-bear/15 blur-3xl" />

      <div className="relative mx-auto flex max-w-5xl flex-col gap-20 px-4 pt-6 pb-16">
        <nav className="flex items-center justify-between">
          <Logo />
          <Button variant="ghost" size="sm" asChild>
            <a href="#how">How it works</a>
          </Button>
        </nav>

        {/* Hero */}
        <section className="flex flex-col items-center gap-6 text-center">
          <Badge variant="outline" className="bg-card/70 text-muted-foreground">
            SEC filings · Gemini · ElevenLabs
          </Badge>
          <h1 className="max-w-3xl font-display text-4xl leading-tight font-bold tracking-tight sm:text-6xl">
            Two AI analysts debate a company’s debt.{" "}
            <span className="bg-linear-to-r from-bull to-bear bg-clip-text text-transparent">You make the call.</span>
          </h1>
          <p className="max-w-xl text-muted-foreground sm:text-lg">
            Most AI tells you what to think. Ours shows you what to check: every claim is labeled and linked to the filing it
            came from.
          </p>

          <form
            className="flex w-full max-w-xl flex-col gap-2 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              go(ticker);
            }}
          >
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="h-12 rounded-xl bg-card pl-10 text-base"
                placeholder="Company name or ticker"
                aria-label="Company name or ticker"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
              />
            </div>
            <Button type="submit" size="lg" className="h-12 rounded-xl px-5 text-base font-semibold" disabled={!!starting}>
              {starting && starting === ticker.trim().toUpperCase() ? <Loader2 className="animate-spin" /> : null}
              Start debate
            </Button>
          </form>
        </section>

        {/* Demo companies */}
        <section className="flex flex-col gap-4">
          <h2 className="text-center text-sm text-muted-foreground">Or pick a demo company</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {companies.map((c) => (
              <button key={c.ticker} onClick={() => go(c.ticker)} disabled={!!starting} className="group text-left disabled:opacity-60">
                <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:ring-foreground/25">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary" className="rounded-sm font-mono">
                        {c.ticker}
                      </Badge>
                      {starting === c.ticker ? (
                        <Loader2 className="size-4 animate-spin text-muted-foreground" />
                      ) : (
                        <ArrowRight className="size-4 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-foreground" />
                      )}
                    </div>
                    <CardTitle className="mt-2">{c.company}</CardTitle>
                    {c.tagline && <CardDescription>{c.tagline}</CardDescription>}
                  </CardHeader>
                </Card>
              </button>
            ))}
          </div>
        </section>

        {/* Preview of the debate floor */}
        <section className="grid items-center gap-8 lg:grid-cols-2">
          <div className="flex flex-col gap-3">
            <h2 className="font-display text-2xl font-bold sm:text-3xl">Hear the debate. Check every claim.</h2>
            <p className="text-muted-foreground">
              A bull and a bear argue from the company’s 10-K, 10-Q and recent news, out loud and in their own voices. An
              independent fact-checker labels each claim against the source text, and you can interrupt with your own
              question at any time.
            </p>
            <ul className="mt-2 flex flex-col gap-2 text-sm">
              <LegendRow label="verified" text="The cited filing says this" />
              <LegendRow label="contested" text="The cited filing says something different" />
              <LegendRow label="unsupported" text="No source backs this up" />
            </ul>
          </div>

          <Card className="gap-3 p-4 shadow-2xl shadow-black/40">
            <PreviewBubble
              side="bull"
              text="Leverage looks high at 5.8x, but the term loan is secured by owned stores. Lenders get paid first."
              chips={[["verified", "10-K · Note 9, p. 84"]]}
            />
            <PreviewBubble
              side="bear"
              text="Sixty-two percent of that debt floats, and a 200 bp move puts coverage near 1.3x."
              chips={[
                ["verified", "10-Q · Liquidity, p. 31"],
                ["contested", "10-Q · Liquidity, p. 31"],
              ]}
            />
            <div className="self-center rounded-lg bg-mod-bg px-4 py-2 text-center text-sm">
              <div className="text-xs font-semibold text-mod uppercase">You asked</div>
              What happens if the stores sell at a discount?
            </div>
          </Card>
        </section>

        {/* How it works */}
        <section id="how" className="flex scroll-mt-8 flex-col gap-6">
          <h2 className="text-center font-display text-2xl font-bold sm:text-3xl">How it works</h2>
          <ol className="grid gap-3 sm:grid-cols-3">
            <Step n={1} title="Research" text="We pull the company’s filings from SEC EDGAR. Python, not AI, computes leverage, coverage and liquidity." />
            <Step n={2} title="Debate" text="Bull and bear argue only from that fact sheet. Every claim cites the passage it relies on." />
            <Step n={3} title="Brief" text="You get what both sides agree on, what’s disputed, what’s unsupported, and where to look next." />
          </ol>
        </section>

        <footer className="border-t pt-6 text-center text-xs text-muted-foreground">
          Bull vs Bear summarizes arguments from public filings. It is not investment advice.
        </footer>
      </div>
    </div>
  );
}

function LegendRow({ label, text }: { label: Label; text: string }) {
  return (
    <li className="flex items-center gap-3">
      <ClaimBadge label={label} className="w-24" />
      <span className="text-neutral-300">{text}</span>
    </li>
  );
}

function PreviewBubble({ side, text, chips }: { side: "bull" | "bear"; text: string; chips: [Label, string][] }) {
  const bull = side === "bull";
  return (
    <div className={`max-w-[88%] rounded-lg p-3 ${bull ? "self-start bg-bull-bg" : "self-end bg-bear-bg"}`}>
      <div className={`mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase ${bull ? "text-bull" : "text-bear"}`}>
        <Mascot side={side} size={18} />
        {bull ? "Bull" : "Bear"}
      </div>
      <p className="text-sm">{text}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {chips.map(([label, source], i) => (
          <ClaimBadge key={i} label={label} source={source} />
        ))}
      </div>
    </div>
  );
}

function Step({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <li>
      <Card className="h-full">
        <CardHeader>
          <span className="grid size-7 place-items-center rounded-full bg-muted font-mono text-xs">{n}</span>
          <CardTitle className="mt-2">{title}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">{text}</CardContent>
      </Card>
    </li>
  );
}

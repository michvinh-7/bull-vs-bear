"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import { startDebate } from "@/lib/api";
import { getCompanies, MOCK_COMPANIES, type DemoCompany } from "@/lib/companies";
import type { Label } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [companies, setCompanies] = useState<DemoCompany[]>(MOCK_COMPANIES);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanies().then(setCompanies);
  }, []);

  async function go(t: string) {
    if (!t.trim() || starting) return;
    setStarting(t.trim().toUpperCase());
    setError(null);
    try {
      const id = await startDebate(t.trim());
      router.push(`/debate/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setStarting(null);
    }
  }

  return (
    <div className="relative overflow-hidden">
      {/* Bull-blue and bear-orange glows behind the hero */}
      <div aria-hidden className="pointer-events-none absolute -left-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-bull/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -right-40 -top-24 h-[28rem] w-[28rem] rounded-full bg-bear/15 blur-3xl" />

      <div className="relative mx-auto flex max-w-5xl flex-col gap-20 px-4 pb-16 pt-6">
        <nav className="flex items-center justify-between">
          <Logo />
          <a href="#how" className="text-sm text-neutral-400 hover:text-white">
            How it works
          </a>
        </nav>

        {/* Hero */}
        <section className="flex flex-col items-center gap-6 text-center">
          <span className="rounded-full border border-line bg-panel/70 px-3 py-1 text-xs text-neutral-400">
            SEC filings · Gemini · ElevenLabs
          </span>
          <h1 className="max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            Two AI analysts debate a company’s debt.{" "}
            <span className="bg-gradient-to-r from-bull to-bear bg-clip-text text-transparent">You make the call.</span>
          </h1>
          <p className="max-w-xl text-neutral-400 sm:text-lg">
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
            <div className="flex flex-1 items-center gap-2 rounded-xl border border-line bg-panel px-4 focus-within:border-neutral-500">
              <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-neutral-500" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
              </svg>
              <input
                className="w-full bg-transparent py-3 outline-none placeholder:text-neutral-500"
                placeholder="Company name or ticker"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
              />
            </div>
            <button
              className="rounded-xl bg-neutral-100 px-5 py-3 font-semibold text-black transition hover:bg-white disabled:opacity-50"
              disabled={!!starting}
            >
              {starting && starting === ticker.trim().toUpperCase() ? "Starting…" : "Start debate"}
            </button>
          </form>
          {error && <p className="text-sm text-unsupported">{error}</p>}
        </section>

        {/* Demo companies */}
        <section className="flex flex-col gap-4">
          <h2 className="text-center text-sm text-neutral-400">Or pick a demo company</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {companies.map((c) => (
              <button
                key={c.ticker}
                onClick={() => go(c.ticker)}
                disabled={!!starting}
                className="group flex flex-col gap-2 rounded-xl border border-line bg-panel p-4 text-left transition hover:-translate-y-0.5 hover:border-neutral-500 disabled:opacity-60"
              >
                <span className="flex items-center justify-between">
                  <span className="rounded bg-bg px-2 py-0.5 font-mono text-xs text-neutral-300">{c.ticker}</span>
                  <span className="text-neutral-500 transition group-hover:translate-x-0.5 group-hover:text-white">
                    {starting === c.ticker ? "…" : "→"}
                  </span>
                </span>
                <span className="font-semibold">{c.company}</span>
                {c.tagline && <span className="text-sm text-neutral-400">{c.tagline}</span>}
              </button>
            ))}
          </div>
        </section>

        {/* Preview of the debate floor */}
        <section className="grid items-center gap-8 lg:grid-cols-2">
          <div className="flex flex-col gap-3">
            <h2 className="font-display text-2xl font-bold sm:text-3xl">Hear the debate. Check every claim.</h2>
            <p className="text-neutral-400">
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

          <div className="flex flex-col gap-3 rounded-2xl border border-line bg-panel p-4 shadow-2xl shadow-black/40">
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
              <div className="text-xs font-semibold uppercase text-mod">You asked</div>
              What happens if the stores sell at a discount?
            </div>
          </div>
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

        <footer className="border-t border-line pt-6 text-center text-xs text-neutral-500">
          Bull vs Bear summarizes arguments from public filings. It is not investment advice.
        </footer>
      </div>
    </div>
  );
}

const CHIP = {
  verified: "border-verified/60 text-verified",
  contested: "border-contested/60 text-contested",
  unsupported: "border-unsupported/60 text-unsupported",
  pending: "border-neutral-600 text-neutral-400",
} satisfies Record<Label, string>;

function LegendRow({ label, text }: { label: Label; text: string }) {
  return (
    <li className="flex items-center gap-3">
      <span className={`w-24 rounded border px-2 py-0.5 text-center font-mono text-xs ${CHIP[label]}`}>{label}</span>
      <span className="text-neutral-300">{text}</span>
    </li>
  );
}

function PreviewBubble({ side, text, chips }: { side: "bull" | "bear"; text: string; chips: [Label, string][] }) {
  const bull = side === "bull";
  return (
    <div className={`max-w-[88%] rounded-lg p-3 ${bull ? "self-start bg-bull-bg" : "self-end bg-bear-bg"}`}>
      <div className={`text-xs font-semibold uppercase ${bull ? "text-bull" : "text-bear"}`}>{bull ? "Bull" : "Bear"}</div>
      <p className="text-sm">{text}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {chips.map(([label, source], i) => (
          <span key={i} className={`rounded border px-2 py-0.5 font-mono text-[11px] ${CHIP[label]}`}>
            {label} · {source}
          </span>
        ))}
      </div>
    </div>
  );
}

function Step({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <li className="flex flex-col gap-2 rounded-xl border border-line bg-panel p-5">
      <span className="grid h-7 w-7 place-items-center rounded-full bg-bg font-mono text-xs text-neutral-300">{n}</span>
      <span className="font-semibold">{title}</span>
      <span className="text-sm text-neutral-400">{text}</span>
    </li>
  );
}

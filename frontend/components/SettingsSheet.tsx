"use client";

import { useEffect, useState } from "react";
import { Check, ExternalLink, Eye, EyeOff, KeyRound, Settings } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { getModels } from "@/lib/api";
import {
  formatTokens,
  formatUsd,
  getApiKey,
  looksLikeKey,
  priceLine,
  resetTotals,
  setApiKey,
  setModel,
  useSettings,
  type Totals,
} from "@/lib/settings";
import type { ModelsResponse, Usage } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Gear button + drawer: Gemini model, the user's own API key, and token/cost usage. */
export default function SettingsSheet({ current }: { current?: Usage | null }) {
  const mobile = useIsMobile();
  const settings = useSettings();
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [modelsError, setModelsError] = useState(false);

  useEffect(() => {
    getModels()
      .then(setModels)
      .catch(() => setModelsError(true));
  }, []);

  const selected = settings.model ?? models?.default;
  const selectedModel = models?.models.find((m) => m.id === selected);
  const needsOwnKey = selected?.includes("pro") && !settings.hasKey;

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Settings" title="Settings">
          <Settings />
        </Button>
      </SheetTrigger>
      <SheetContent side={mobile ? "bottom" : "right"} className="max-h-[90vh] gap-0 overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Settings</SheetTitle>
          <SheetDescription>Model and key apply to the next debate you start.</SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-8 px-4 pb-8">
          {/* Model */}
          <Section title="Gemini model">
            {modelsError && <p className="text-sm text-muted-foreground">Couldn’t load the model list. The server default will be used.</p>}
            <div role="radiogroup" aria-label="Gemini model" className="flex flex-col gap-2">
              {models?.models.map((m) => {
                const on = m.id === selected;
                return (
                  <button
                    key={m.id}
                    role="radio"
                    aria-checked={on}
                    onClick={() => setModel(m.id)}
                    className={cn(
                      "flex items-start gap-3 rounded-lg border p-3 text-left transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden",
                      on && "border-foreground/40 bg-accent",
                    )}
                  >
                    <span className={cn("mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border", on && "border-foreground bg-foreground text-background")}>
                      {on && <Check className="size-3" />}
                    </span>
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        {m.label}
                        {m.id === models.default && <Badge variant="secondary">Default</Badge>}
                      </span>
                      <span className="text-xs text-muted-foreground">{m.note}</span>
                      <span className="font-mono text-[11px] text-muted-foreground">{priceLine(m)}</span>
                      {m.price_note && <span className="text-[11px] text-muted-foreground">{m.price_note}</span>}
                    </span>
                  </button>
                );
              })}
            </div>
            {needsOwnKey && (
              <p className="rounded-md bg-contested/10 p-2 text-xs text-contested">
                Pro usually needs your own API key with Pro access. With the team key, debates on Pro may fail.
              </p>
            )}
          </Section>

          {/* API key */}
          <Section title="Your Gemini API key" optional>
            <KeyField hasKey={settings.hasKey} />
          </Section>

          {/* Usage */}
          <Section title="Usage">
            {current && <UsageCard title="This debate" usage={current} />}
            <UsageCard title="All debates in this browser" usage={settings.totals} onReset={resetTotals} />
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Costs are estimates from Google’s published prices
              {models ? ` (checked ${models.prices_checked})` : ""}, with thinking tokens billed as output. Your actual bill may
              differ. Voice is counted in ElevenLabs characters.
              {selectedModel ? ` Selected: ${selectedModel.label}.` : ""}
            </p>
          </Section>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Section({ title, optional, children }: { title: string; optional?: boolean; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold">
        {title}
        {optional && <span className="ml-1.5 font-normal text-muted-foreground">(optional)</span>}
      </h3>
      {children}
    </section>
  );
}

function KeyField({ hasKey }: { hasKey: boolean }) {
  const [draft, setDraft] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const masked = hasKey ? `••••${(getApiKey() ?? "").slice(-4)}` : null;

  function save() {
    if (!looksLikeKey(draft)) {
      setError("That doesn’t look like a Gemini API key.");
      return;
    }
    setApiKey(draft);
    setDraft("");
    setError(null);
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs leading-relaxed text-muted-foreground">
        Use your own key instead of the team’s. It’s sent only to our server, with each debate you start, and kept in this
        browser tab until you close it. It’s never saved or shown to anyone.
      </p>
      {hasKey ? (
        <div className="flex items-center justify-between gap-2 rounded-lg border p-3">
          <span className="flex items-center gap-2 text-sm">
            <KeyRound className="size-4 text-verified" />
            Using your key <span className="font-mono text-xs text-muted-foreground">{masked}</span>
          </span>
          <Button variant="outline" size="sm" onClick={() => setApiKey(null)}>
            Remove
          </Button>
        </div>
      ) : (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <div className="relative flex-1">
            <Input
              type={show ? "text" : "password"}
              placeholder="Paste your Gemini API key"
              aria-label="Gemini API key"
              autoComplete="off"
              spellCheck={false}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="pr-9 font-mono text-xs"
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              aria-label={show ? "Hide key" : "Show key"}
              className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
          <Button type="submit" disabled={!draft.trim()}>
            Use key
          </Button>
        </form>
      )}
      {error && <p className="text-xs text-unsupported">{error}</p>}
      <a
        href="https://aistudio.google.com/apikey"
        target="_blank"
        rel="noreferrer"
        className="inline-flex w-fit items-center gap-1 text-xs text-bull hover:underline"
      >
        Get a key from Google AI Studio <ExternalLink className="size-3" />
      </a>
    </div>
  );
}

function UsageCard({ title, usage, onReset }: { title: string; usage: Usage | Totals; onReset?: () => void }) {
  const isTotals = "debates" in usage;
  const unpriced = isTotals ? usage.unpriced_debates : usage.cost_usd === null ? 1 : 0;
  const rows: [string, string][] = [
    ["Gemini calls", String(usage.calls)],
    ["Input tokens", formatTokens(usage.input_tokens)],
    ["Output tokens", formatTokens(usage.output_tokens)],
    ["Thinking tokens", formatTokens(usage.thinking_tokens)],
    ["Voice characters", formatTokens(usage.voice_chars)],
  ];
  return (
    <div className="flex flex-col gap-3 rounded-lg border p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground uppercase">{title}</span>
        {isTotals && <span className="text-xs text-muted-foreground">{usage.debates} debates</span>}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-2xl">{formatUsd(isTotals ? usage.cost_usd : usage.cost_usd)}</span>
        <span className="text-xs text-muted-foreground">estimated Gemini cost</span>
      </div>
      {unpriced > 0 && (
        <p className="text-[11px] text-muted-foreground">
          {isTotals ? `${unpriced} debate(s) used a model without a known price and aren’t included.` : "This model’s price isn’t known."}
        </p>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="text-right font-mono">{v}</dd>
          </div>
        ))}
      </dl>
      {onReset && (
        <Button variant="ghost" size="sm" className="self-end" onClick={onReset} disabled={usage.calls === 0 && usage.voice_chars === 0}>
          Reset
        </Button>
      )}
    </div>
  );
}

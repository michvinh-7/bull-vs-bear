"use client";

import { Card } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { findSource } from "@/lib/format";
import { formatUsd, maturityWall, type MaturityBucket } from "@/lib/maturity";
import type { DebtInstrument, FactSheet } from "@/lib/types";
import { cn } from "@/lib/utils";

const SENIORITY: Record<DebtInstrument["seniority"], string> = {
  senior_secured: "Senior secured",
  senior_unsecured: "Senior unsecured",
  subordinated: "Subordinated",
};

/**
 * When the company's debt comes due, year by year, split into fixed and floating rate.
 * Built from the fact sheet's debt table; every number is added up in code, not by the AI.
 */
export default function MaturityWall({ sheet, className }: { sheet: FactSheet; className?: string }) {
  const wall = maturityWall(sheet);
  if (!wall) return null;

  const max = Math.max(...wall.buckets.map((b) => b.total_usd));
  const nearEnd = wall.start_year + 2;
  const hasFloating = wall.buckets.some((b) => b.floating_usd > 0);

  return (
    <Card className={cn("gap-4 p-5", className)}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-semibold">Maturity wall</h2>
          <p className="text-sm text-muted-foreground">When the debt comes due, and how much of it floats.</p>
        </div>
        <dl className="grid grid-cols-3 gap-4 text-right sm:gap-6">
          <Stat label="In debt table" value={formatUsd(wall.total_usd)} />
          <Stat
            label={`Due by ${nearEnd}`}
            value={`${Math.round(wall.near_term_pct)}%`}
            tone={wall.near_term_pct >= 25 ? "text-contested" : undefined}
          />
          <Stat label="Peak" value={wall.peak ? wall.peak.label : "–"} />
        </dl>
      </div>

      {/* Bars grow up from a shared baseline; empty years keep their slot so gaps show. */}
      <div className="flex h-44 items-end gap-1 border-b pb-px sm:gap-2" role="list" aria-label="Debt due by year">
        {wall.buckets.map((b) => (
          <Bar key={b.from} bucket={b} max={max} near={b.to <= nearEnd} sheet={sheet} />
        ))}
      </div>
      <div className="-mt-2 flex gap-1 sm:gap-2" aria-hidden>
        {wall.buckets.map((b) => (
          <div
            key={b.from}
            className={cn(
              "min-w-0 flex-1 text-center font-mono text-[10px] leading-tight text-muted-foreground",
              b.to <= nearEnd && "font-semibold text-foreground",
            )}
          >
            {b.from === b.to ? (
              <>
                <span className="sm:hidden">’{String(b.from).slice(-2)}</span>
                <span className="hidden sm:inline">{b.from}</span>
              </>
            ) : (
              <>
                <span className="flex flex-col sm:hidden">
                  <span>’{String(b.from).slice(-2)}</span>
                  <span className="opacity-70">{String(b.to).slice(-2)}</span>
                </span>
                <span className="hidden sm:inline">{b.label}</span>
              </>
            )}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <Legend swatch="bg-muted-foreground/60" text="Fixed rate" />
        {hasFloating && <Legend swatch="bg-contested" text="Floating rate (moves with interest rates)" />}
        <span className="sm:ml-auto">
          Added up in code from the {wall.buckets.reduce((n, b) => n + b.instruments.length, 0)} instruments in the fact
          sheet’s debt table, which may not list every loan. Hover a bar for details.
        </span>
      </div>
    </Card>
  );
}

function Bar({ bucket: b, max, near, sheet }: { bucket: MaturityBucket; max: number; near: boolean; sheet: FactSheet }) {
  // The tallest bar stops short of the top so its amount label still fits above it.
  const pct = (v: number) => (max > 0 ? (v / max) * 85 : 0);
  const years = b.from === b.to ? String(b.from) : `${b.from} to ${b.to}`;
  const summary = b.total_usd
    ? `${years}: ${formatUsd(b.total_usd)} due${b.floating_usd ? `, ${formatUsd(b.floating_usd)} floating` : ""}`
    : `${years}: nothing due`;

  if (!b.total_usd) {
    return <div role="listitem" aria-label={summary} className="h-full min-w-0 flex-1" />;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          role="listitem"
          tabIndex={0}
          aria-label={summary}
          className="group flex h-full min-w-0 flex-1 cursor-help flex-col justify-end rounded-t-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="mb-1 hidden text-center font-mono text-[10px] text-muted-foreground sm:block">
            {formatUsd(b.total_usd)}
          </span>
          <div
            className={cn(
              "flex w-full flex-col overflow-hidden rounded-t-sm transition-opacity group-hover:opacity-80",
              near && "ring-1 ring-foreground/30",
            )}
            style={{ height: `${Math.max(pct(b.total_usd), 2)}%` }}
          >
            {b.floating_usd > 0 && <div className="bg-contested" style={{ flexGrow: b.floating_usd }} />}
            {b.fixed_usd > 0 && <div className="bg-muted-foreground/60" style={{ flexGrow: b.fixed_usd }} />}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-72">
        <div className="flex flex-col gap-1.5">
          <span className="font-semibold">
            {years} · {formatUsd(b.total_usd)}
          </span>
          <ul className="flex flex-col gap-1">
            {b.instruments.map((d, i) => (
              <li key={i} className="flex flex-col">
                <span>
                  {d.name} · <span className="font-mono">{formatUsd(d.amount_usd)}</span>
                </span>
                <span className="opacity-70">
                  {d.rate} · {d.rate_type} rate · {SENIORITY[d.seniority]}
                  {b.from !== b.to ? ` · ${d.maturity_year}` : ""}
                  {findSource(sheet, d.source_id) ? ` · ${findSource(sheet, d.source_id)!.label}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("font-mono text-lg", tone)}>{value}</dd>
    </div>
  );
}

function Legend({ swatch, text }: { swatch: string; text: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("size-2.5 rounded-sm", swatch)} />
      {text}
    </span>
  );
}

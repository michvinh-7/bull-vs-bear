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
 * Bar heights come from the 10-K's maturity schedule when the fact sheet has one, and the
 * split from its debt table; every number is added up in code, not by the AI.
 */
export default function MaturityWall({ sheet, className }: { sheet: FactSheet; className?: string }) {
  const wall = maturityWall(sheet);
  if (!wall) return null;

  // "thereafter" can be decades of debt in one bar; it would flatten the wall, so it's scaled
  // with the yearly bars and drawn cut off at the top instead
  const yearly = wall.buckets.filter((b) => !b.thereafter);
  const max = Math.max(...(yearly.length ? yearly : wall.buckets).map((b) => b.total_usd));
  const nearEnd = wall.start_year + 2;
  const hasFloating = wall.buckets.some((b) => b.floating_usd > 0);
  const hasUnlisted = wall.buckets.some((b) => b.unlisted_usd > 0);
  const scheduleSource = findSource(sheet, sheet.maturities_source_id ?? null);

  return (
    <Card className={cn("gap-4 p-5", className)}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-semibold">Maturity wall</h2>
          <p className="text-sm text-muted-foreground">When the debt comes due, and how much of it floats.</p>
        </div>
        <dl className="grid grid-cols-3 gap-4 text-right sm:gap-6">
          <Stat label={wall.complete ? "Total debt" : "In debt table"} value={formatUsd(wall.total_usd)} />
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
          <Bar key={b.from} bucket={b} max={max} near={b.to <= nearEnd} sheet={sheet} fromSchedule={wall.from_schedule} />
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
            {b.thereafter ? (
              <>
                <span className="sm:hidden">’{String(b.from).slice(-2)}+</span>
                <span className="hidden sm:inline">{b.label}</span>
              </>
            ) : b.from === b.to ? (
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
        {hasUnlisted && <Legend swatch="bg-muted-foreground/25" text="Not in the debt table" />}
        <span className="sm:ml-auto">
          {wall.from_schedule ? (
            <>
              Bars from the 10-K’s debt maturity schedule{scheduleSource ? ` (${scheduleSource.label})` : ""}; the
              fixed/floating split covers the {wall.instrument_count} largest instruments in the debt table. Hover a bar
              for details.
            </>
          ) : (
            <>
              Added up in code from the {wall.instrument_count} instruments in the fact sheet’s debt table, which may not
              list every loan. Hover a bar for details.
            </>
          )}
        </span>
      </div>
    </Card>
  );
}

function Bar({
  bucket: b,
  max,
  near,
  sheet,
  fromSchedule,
}: {
  bucket: MaturityBucket;
  max: number;
  near: boolean;
  sheet: FactSheet;
  fromSchedule: boolean;
}) {
  // The tallest bar stops short of the top so its amount label still fits above it.
  const pct = (v: number) => (max > 0 ? (v / max) * 85 : 0);
  const cutOff = b.thereafter && b.total_usd > max;
  const height = cutOff ? 85 : Math.max(pct(b.total_usd), 2);
  const years = b.thereafter ? `${b.from} and later` : b.from === b.to ? String(b.from) : `${b.from} to ${b.to}`;
  const listed = b.fixed_usd + b.floating_usd;
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
              cutOff && "rounded-t-none border-t-2 border-dashed border-background",
            )}
            style={{ height: `${height}%` }}
          >
            {b.unlisted_usd > 0 && <div className="bg-muted-foreground/25" style={{ flexGrow: b.unlisted_usd }} />}
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
          {fromSchedule && (
            <span className="opacity-70">
              {b.thereafter ? "All debt due after the schedule’s last year, lumped together in the 10-K. " : ""}
              {b.instruments.length === 0
                ? "None of it is among the largest instruments in the debt table."
                : b.unlisted_usd > 0
                  ? `${formatUsd(listed)} of it is in the debt table:`
                  : "From the debt table:"}
            </span>
          )}
          <ul className="flex flex-col gap-1">
            {b.instruments.map((d, i) => (
              <li key={i} className="flex flex-col">
                <span>
                  {d.name} · <span className="font-mono">{formatUsd(d.amount_usd)}</span>
                </span>
                <span className="opacity-70">
                  {d.rate} · {d.rate_type} rate · {SENIORITY[d.seniority]}
                  {b.from !== b.to || b.thereafter ? ` · ${d.maturity_year}` : ""}
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

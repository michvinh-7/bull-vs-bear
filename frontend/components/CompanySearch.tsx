"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Loader2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { resolveTicker, searchCompanies, type DemoCompany } from "@/lib/companies";
import { cn } from "@/lib/utils";

/**
 * Search box with type-ahead suggestions from GET /companies/search
 * (demo companies first, then SEC's ~10k public companies).
 */
export default function CompanySearch({ onPick, busy }: { onPick: (ticker: string) => void; busy: boolean }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DemoCompany[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const blurTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Debounced search; stale responses are cancelled.
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      searchCompanies(query, ctrl.signal)
        .then((r) => {
          setResults(r);
          setActive(-1);
        })
        .catch(() => {});
    }, 180);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [query]);

  function pick(ticker: string) {
    setOpen(false);
    onPick(ticker);
  }

  const showList = open && results.length > 0;

  return (
    <form
      className="flex w-full max-w-xl flex-col gap-2 sm:flex-row"
      onSubmit={(e) => {
        e.preventDefault();
        if (query.trim()) pick(active >= 0 ? results[active].ticker : resolveTicker(query, results));
      }}
    >
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-4 z-10 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="h-12 rounded-xl bg-card pl-10 text-base"
          placeholder="Company name or ticker"
          aria-label="Company name or ticker"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          autoComplete="off"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => (blurTimer.current = setTimeout(() => setOpen(false), 120))}
          onKeyDown={(e) => {
            if (!showList) return;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => (a + 1) % results.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => (a <= 0 ? results.length - 1 : a - 1));
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
        />
        {showList && (
          <ul
            id={listId}
            role="listbox"
            className="absolute inset-x-0 top-full z-30 mt-1.5 max-h-80 overflow-y-auto rounded-xl border bg-popover p-1 text-left shadow-2xl shadow-black/50"
          >
            {results.map((c, i) => (
              <li
                key={c.ticker}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                // mousedown, not click, so the input doesn't blur and close the list first
                onMouseDown={(e) => {
                  e.preventDefault();
                  clearTimeout(blurTimer.current);
                  pick(c.ticker);
                }}
                onMouseEnter={() => setActive(i)}
                className={cn("flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2", i === active && "bg-accent")}
              >
                <Badge variant="secondary" className="w-16 shrink-0 justify-center rounded-sm font-mono">
                  {c.ticker}
                </Badge>
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-sm">{c.company}</span>
                  {c.tagline && <span className="truncate text-xs text-muted-foreground">Demo · {c.tagline}</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <Button type="submit" size="lg" className="h-12 rounded-xl px-5 text-base font-semibold" disabled={busy}>
        {busy && <Loader2 className="animate-spin" />}
        Start debate
      </Button>
    </form>
  );
}

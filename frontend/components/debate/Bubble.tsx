import ClaimBadge from "@/components/ClaimBadge";
import { findSource } from "@/lib/format";
import type { Claim, FactSheet, LineMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SPEAKER } from "./speakers";

interface Props {
  line: LineMessage;
  sheet: FactSheet | null;
  /** True while this line's clip is playing. */
  active: boolean;
  /** 0..1 through the clip; drives the typing reveal. */
  progress: number;
  onClaim: (claim: Claim, line: LineMessage) => void;
}

export default function Bubble({ line, sheet, active, progress, onClaim }: Props) {
  const s = SPEAKER[line.speaker];
  // Text runs slightly ahead of the voice, then the claim labels pop in.
  const reveal = active ? Math.min(1, progress * 1.15) : 1;
  const text = reveal < 1 ? line.text.slice(0, Math.ceil(line.text.length * reveal)) : line.text;

  return (
    <div
      className={cn(
        "max-w-[88%] rounded-lg p-3 transition-shadow duration-300 animate-in fade-in-0 slide-in-from-bottom-2",
        s.bg,
        s.align,
        active && `ring-2 ${s.ring}`,
      )}
    >
      <div className={cn("text-xs font-semibold uppercase", s.text)}>{line.from_user ? "You asked" : s.name}</div>
      <p className="text-sm leading-relaxed">
        {text}
        {reveal < 1 && (
          <span className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 bg-current" style={{ animation: "caret 1s steps(1) infinite" }} />
        )}
      </p>
      {reveal === 1 && line.claims.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1 animate-in fade-in-0">
          {line.claims.map((c) => (
            <button key={c.id} title={c.text} onClick={() => onClaim(c, line)} className="rounded-sm focus-visible:ring-2 focus-visible:ring-ring">
              <ClaimBadge label={c.label} source={findSource(sheet, c.source_id)?.label ?? "no source"} className="cursor-pointer hover:brightness-125" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

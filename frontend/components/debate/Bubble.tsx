import { Gavel, MessageCircleQuestion } from "lucide-react";
import ClaimBadge from "@/components/ClaimBadge";
import { findSource } from "@/lib/format";
import type { Claim, FactSheet, LineMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import Mascot from "./Mascot";
import { SPEAKER } from "./speakers";

interface Props {
  line: LineMessage;
  sheet: FactSheet | null;
  /** True while this line's clip is playing. */
  active: boolean;
  /** 0..1 through the clip; drives the typing reveal. */
  progress: number;
  onClaim: (claim: Claim, line: LineMessage) => void;
  /** Show the one-time "tap a label" hint under this bubble's labels. */
  hint?: boolean;
}

export default function Bubble({ line, sheet, active, progress, onClaim, hint }: Props) {
  const s = SPEAKER[line.speaker];
  // Text runs slightly ahead of the voice; the claim labels stamp in when it stops.
  const reveal = active ? Math.min(1, progress * 1.15) : 1;
  const text = reveal < 1 ? line.text.slice(0, Math.ceil(line.text.length * reveal)) : line.text;

  return (
    <div
      className={cn(
        "max-w-[88%] rounded-lg p-3 transition-shadow duration-300 animate-in fade-in-0",
        line.speaker === "bull" ? "slide-in-from-left-4" : line.speaker === "bear" ? "slide-in-from-right-4" : "slide-in-from-bottom-2",
        s.bg,
        s.align,
        active && `ring-2 ${s.ring}`,
      )}
    >
      <div className={cn("mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase", s.text, line.speaker === "moderator" && "justify-center")}>
        {line.speaker === "moderator" ? (
          line.from_user ? <MessageCircleQuestion className="size-3.5" /> : <Gavel className="size-3.5" />
        ) : (
          <Mascot side={line.speaker} size={18} />
        )}
        {line.from_user ? "You asked" : s.name}
      </div>
      <p className="text-sm leading-relaxed">
        {text}
        {reveal < 1 && (
          <span className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 bg-current" style={{ animation: "caret 1s steps(1) infinite" }} />
        )}
      </p>
      {!active && line.claims.length > 0 && (
        <>
          <div className="mt-2 flex flex-wrap gap-1">
            {line.claims.map((c, i) => (
              <button
                key={c.id}
                title={c.text}
                onClick={() => onClaim(c, line)}
                className={cn(
                  "rounded-sm focus-visible:ring-2 focus-visible:ring-ring",
                  hint && i === 0 && "ring-2 ring-foreground/50 ring-offset-2 ring-offset-transparent",
                )}
                style={{ animation: `stamp 0.45s ease-out ${0.1 + i * 0.25}s both` }}
              >
                <ClaimBadge
                  label={c.label}
                  source={findSource(sheet, c.source_id)?.label ?? "no source"}
                  className="cursor-pointer hover:brightness-125"
                />
              </button>
            ))}
          </div>
          {hint && (
            <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground animate-in fade-in-0">
              <span className="text-foreground">↑</span> Tap a label to see the source it came from
            </p>
          )}
        </>
      )}
    </div>
  );
}

import { Card } from "@/components/ui/card";
import type { LineMessage, Position, Side } from "@/lib/types";
import { cn } from "@/lib/utils";
import Mascot from "./Mascot";
import { SPEAKER } from "./speakers";
import Waveform from "./Waveform";

export type PanelStatus = "speaking" | "thinking" | "waiting";

const STATUS_TEXT: Record<PanelStatus, string> = {
  speaking: "Speaking now",
  thinking: "Thinking…",
  waiting: "Waiting",
};

export default function SidePanel({
  side,
  position,
  heard,
  status,
  paused,
}: {
  side: Side;
  position?: Position;
  heard: LineMessage[];
  status: PanelStatus;
  paused: boolean;
}) {
  const s = SPEAKER[side];
  // Replaces "points scored": how many of this side's claims (so far) were verified.
  const verified = heard
    .filter((l) => l.speaker === side)
    .flatMap((l) => l.claims)
    .filter((c) => c.label === "verified").length;

  return (
    <Card className={cn("gap-4 p-5 transition-shadow duration-300", status === "speaking" && `ring-2 ${s.ring}`)}>
      <div className="flex items-center gap-3">
        <span className={cn("grid size-14 place-items-center rounded-full", s.bg)}>
          <Mascot side={side} speaking={status === "speaking" && !paused} size={44} />
        </span>
        <div>
          <div className={cn("font-semibold", s.text)}>{s.name}</div>
          <div className="text-sm text-muted-foreground">{STATUS_TEXT[status]}</div>
        </div>
      </div>
      <Waveform active={status === "speaking"} color={s.bar} paused={paused} />
      {position && (
        <div className="flex flex-col gap-2">
          <div className="text-xs text-muted-foreground uppercase">Thesis</div>
          <p className="text-sm">{position.thesis}</p>
          <ul className="mt-1 space-y-1.5 text-sm text-foreground/85">
            {position.points.map((p, i) => (
              <li key={i} className="flex gap-2">
                <span className={s.text}>{side === "bull" ? "+" : "−"}</span>
                {p.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-auto text-xs text-muted-foreground">Verified claims · {verified}</div>
    </Card>
  );
}

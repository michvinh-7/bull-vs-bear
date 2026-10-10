import { cn } from "@/lib/utils";

const HEIGHTS = [40, 75, 55, 90, 60, 100, 45, 80, 65, 95, 50, 70, 85, 55, 75, 45];

/** Animated bars while speaking; a flat dashed line otherwise (as in the mockup). */
export default function Waveform({ active, color, paused }: { active: boolean; color: string; paused?: boolean }) {
  return (
    <div className="flex h-6 items-center gap-1" aria-hidden>
      {HEIGHTS.map((h, i) =>
        active ? (
          <span
            key={i}
            className={cn("w-1 rounded-full", color)}
            style={{
              height: `${h}%`,
              animation: `wave ${0.7 + (i % 5) * 0.12}s ease-in-out ${i * 0.05}s infinite`,
              animationPlayState: paused ? "paused" : "running",
            }}
          />
        ) : (
          <span key={i} className="h-0.5 w-2 rounded-full bg-muted-foreground/40" />
        ),
      )}
    </div>
  );
}

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Label } from "@/lib/types";

export const LABEL_STYLE: Record<Label, string> = {
  verified: "border-verified/60 text-verified",
  contested: "border-contested/60 text-contested",
  unsupported: "border-unsupported/60 text-unsupported",
  pending: "border-neutral-600 text-neutral-400",
};

/** A claim's fact-check label, optionally followed by its citation. */
export default function ClaimBadge({ label, source, className }: { label: Label; source?: string; className?: string }) {
  return (
    <Badge variant="outline" className={cn("rounded-sm font-mono text-[11px] font-normal", LABEL_STYLE[label], className)}>
      {label}
      {source && <span className="opacity-80">· {source}</span>}
    </Badge>
  );
}

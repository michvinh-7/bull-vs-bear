"use client";

import { ExternalLink } from "lucide-react";
import ClaimBadge from "@/components/ClaimBadge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { findSource } from "@/lib/format";
import type { Claim, FactSheet, Label, Speaker } from "@/lib/types";
import { SPEAKER } from "./speakers";

const MEANING: Record<Label, string> = {
  verified: "The cited passage supports this claim.",
  contested: "The cited passage says something different from this claim.",
  unsupported: "No passage in the filings backs this claim up.",
  pending: "The fact-checker hasn’t finished with this claim yet.",
};

export interface SelectedClaim {
  claim: Claim;
  speaker: Speaker;
}

/** Click a claim, see exactly what the fact-checker read. */
export default function SourceSheet({
  selected,
  sheet,
  onClose,
}: {
  selected: SelectedClaim | null;
  sheet: FactSheet | null;
  onClose: () => void;
}) {
  const mobile = useIsMobile();
  const source = selected ? findSource(sheet, selected.claim.source_id) : undefined;

  return (
    <Sheet open={!!selected} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side={mobile ? "bottom" : "right"} className="max-h-[85vh] overflow-y-auto">
        {selected && (
          <>
            <SheetHeader>
              <SheetTitle>Claim check</SheetTitle>
              <SheetDescription>{MEANING[selected.claim.label]}</SheetDescription>
            </SheetHeader>
            <div className="flex flex-col gap-5 px-4 pb-6">
              <div className="flex flex-col gap-2">
                <ClaimBadge label={selected.claim.label} />
                <p className="text-base">
                  <span className={SPEAKER[selected.speaker].text}>{SPEAKER[selected.speaker].name}: </span>“{selected.claim.text}”
                </p>
              </div>

              {source ? (
                <div className="flex flex-col gap-2">
                  <div className="text-xs text-muted-foreground uppercase">What the fact-checker read</div>
                  <div className="font-mono text-xs text-muted-foreground">{source.label}</div>
                  <blockquote className="border-l-2 border-muted-foreground/40 pl-3 text-sm leading-relaxed">{source.excerpt}</blockquote>
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex w-fit items-center gap-1 text-sm text-bull hover:underline"
                    >
                      Open the {source.kind === "news" ? "article" : "filing"} <ExternalLink className="size-3.5" />
                    </a>
                  )}
                </div>
              ) : (
                <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
                  This claim didn’t cite a source from the fact sheet, so there’s nothing to check it against.
                </p>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

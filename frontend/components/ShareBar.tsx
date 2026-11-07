"use client";

import { useEffect, useState } from "react";
import { Check, Copy, FileDown, Link2, Share2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { briefMarkdown, linkedInShareUrl } from "@/lib/briefExport";
import type { Debate } from "@/lib/types";

/** The Clipboard API, falling back to a hidden textarea where it's blocked (embedded browsers, http). */
async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta);
    ta.select();
    try {
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      ta.remove();
    }
  }
}

/**
 * Print as a light page whatever theme is on screen: dark backgrounds waste ink
 * and some browsers drop them anyway, leaving light text on white.
 */
export function usePrintInLight() {
  useEffect(() => {
    const html = document.documentElement;
    let wasDark = false;
    const before = () => {
      wasDark = html.classList.contains("dark");
      html.classList.remove("dark");
      html.style.colorScheme = "light";
    };
    const after = () => {
      if (!wasDark) return;
      html.classList.add("dark");
      html.style.colorScheme = "dark";
    };
    window.addEventListener("beforeprint", before);
    window.addEventListener("afterprint", after);
    return () => {
      window.removeEventListener("beforeprint", before);
      window.removeEventListener("afterprint", after);
    };
  }, []);
}

/** Share link, LinkedIn, copy as Markdown, and save as PDF (the browser's print dialog). */
export default function ShareBar({ debate }: { debate: Debate }) {
  const [copied, setCopied] = useState<"link" | "md" | null>(null);
  const [canShare, setCanShare] = useState(false);
  usePrintInLight();

  const [pageUrl, setPageUrl] = useState("");
  useEffect(() => {
    setCanShare("share" in navigator);
    setPageUrl(window.location.href.split(/[?#]/)[0]);
  }, []);

  const url = () => window.location.href.split(/[?#]/)[0];
  const done = (what: "link" | "md", ok: boolean, message: string) => {
    if (!ok) {
      toast.error("Couldn’t copy. Your browser blocked the clipboard.");
      return;
    }
    toast.success(message);
    setCopied(what);
    setTimeout(() => setCopied((c) => (c === what ? null : c)), 2000);
  };

  const shareLink = async () => {
    const company = debate.fact_sheet?.company ?? debate.ticker;
    if (canShare) {
      try {
        await navigator.share({ title: `Committee brief: ${company}`, url: url() });
        return;
      } catch (e) {
        if ((e as Error).name === "AbortError") return; // the user closed the share sheet
      }
    }
    done("link", await copy(url()), "Link copied");
  };

  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      <Button variant="outline" size="sm" onClick={shareLink}>
        {copied === "link" ? <Check /> : canShare ? <Share2 /> : <Link2 />}
        {canShare ? "Share" : "Copy link"}
      </Button>
      <Button asChild variant="outline" size="sm">
        <a href={linkedInShareUrl(pageUrl)} target="_blank" rel="noopener noreferrer">
          <LinkedInIcon /> LinkedIn
        </a>
      </Button>
      <Button variant="outline" size="sm" onClick={async () => done("md", await copy(briefMarkdown(debate, url())), "Brief copied as Markdown")}>
        {copied === "md" ? <Check /> : <Copy />} Copy as Markdown
      </Button>
      <Button variant="outline" size="sm" onClick={() => window.print()}>
        <FileDown /> Save as PDF
      </Button>
    </div>
  );
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className="size-4">
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}

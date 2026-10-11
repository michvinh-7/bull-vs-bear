"use client";

import Link from "next/link";
import { House } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Back to the home page to pick another company. If a live debate is still being
 * generated, asks first: leaving ends it for good (it never resumes).
 */
export default function NewDebateButton({ confirmLeave = false }: { confirmLeave?: boolean }) {
  return (
    <Button asChild variant="ghost" size="sm">
      <Link
        href="/"
        onClick={(e) => {
          if (confirmLeave && !window.confirm("Leave this debate? It ends here and can't be resumed.")) e.preventDefault();
        }}
        aria-label="New debate"
        title="New debate"
      >
        <House />
        <span className="hidden sm:inline">New debate</span>
      </Link>
    </Button>
  );
}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { DoorOpen, Menu } from "lucide-react";
import BrandMark from "@/components/BrandMark";
import SettingsSheet from "@/components/SettingsSheet";
import { ThemeToggle } from "@/components/theme";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { Usage } from "@/lib/types";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Debate" },
  { href: "/#how", label: "How it works" },
  { href: "/history", label: "History" },
  { href: "/team", label: "Team" },
];

function isActive(pathname: string, href: string) {
  if (href.includes("#")) return false;
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
}

function Brand() {
  return (
    <Link href="/" className="flex min-w-0 items-center gap-2.5" aria-label="Bull vs Bear, home">
      <BrandMark size={32} />
      <span className="flex min-w-0 flex-col gap-1">
        <strong className="font-display text-base leading-none font-bold tracking-tight">
          <span className="text-bull">Bull</span> <span className="text-xs font-medium text-muted-foreground">vs</span>{" "}
          <span className="text-bear">Bear</span>
        </strong>
        <small className="truncate font-mono text-[10px] leading-none tracking-[0.08em] text-muted-foreground uppercase">
          AI credit committee
        </small>
      </span>
    </Link>
  );
}

/**
 * The one header every page shares: brand, numbered nav, settings and theme.
 * `confirmLeave` asks before navigating away from a debate that's still being generated.
 */
export default function SiteHeader({
  usage,
  confirmLeave = false,
  actions,
}: {
  usage?: Usage | null;
  confirmLeave?: boolean;
  actions?: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [leavingTo, setLeavingTo] = useState<string | null>(null);

  function navLink(item: (typeof NAV)[number], i: number, mobile = false) {
    const active = isActive(pathname, item.href);
    return (
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        onClick={(e) => {
          if (!confirmLeave) return;
          e.preventDefault();
          setLeavingTo(item.href);
        }}
        className={cn(
          "block rounded-sm border font-mono transition-colors",
          mobile ? "px-3 py-3 text-sm" : "px-3 py-2 text-xs",
          active
            ? "border-border bg-accent text-foreground"
            : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
        )}
      >
        <span className={cn("mr-1.5 text-bull", mobile ? "text-xs" : "text-[10px]")}>0{i + 1}</span>
        {item.label}
      </Link>
    );
  }

  return (
    <header className="sticky top-0 z-40 bg-background/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 border-b px-4 sm:px-6">
        <div className="min-w-0 flex-1 lg:flex-none xl:min-w-56">
          <Brand />
        </div>

        <nav aria-label="Main" className="hidden flex-1 justify-center lg:flex">
          <ul className="flex gap-1">
            {NAV.map((item, i) => (
              <li key={item.href}>{navLink(item, i)}</li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-1 xl:min-w-56 xl:justify-end">
          {actions}
          <SettingsSheet current={usage} />
          <ThemeToggle />
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open menu">
                <Menu />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetHeader>
                <SheetTitle className="font-mono text-xs tracking-[0.12em] text-muted-foreground uppercase">Navigate</SheetTitle>
              </SheetHeader>
              <nav aria-label="Mobile" className="flex flex-col gap-1 px-4">
                {NAV.map((item, i) => (
                  <SheetClose asChild key={item.href}>
                    {navLink(item, i, true)}
                  </SheetClose>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      <AlertDialog open={leavingTo !== null} onOpenChange={(open) => !open && setLeavingTo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-unsupported/10 text-unsupported">
              <DoorOpen />
            </AlertDialogMedia>
            <AlertDialogTitle>Leave this debate?</AlertDialogTitle>
            <AlertDialogDescription>
              The committee is still talking. Leaving ends this debate for good: it can’t be resumed, and a new one starts from
              scratch.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep watching</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => leavingTo && router.push(leavingTo)}>
              Leave debate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}

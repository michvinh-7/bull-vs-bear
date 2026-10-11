"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { DoorOpen, House } from "lucide-react";
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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

function Label() {
  return (
    <>
      <House />
      <span className="hidden sm:inline">New debate</span>
    </>
  );
}

/**
 * Back to the home page to pick another company. If a live debate is still being
 * generated, asks first: leaving ends it for good (it never resumes).
 */
export default function NewDebateButton({ confirmLeave = false }: { confirmLeave?: boolean }) {
  const router = useRouter();

  if (!confirmLeave) {
    return (
      <Button asChild variant="ghost" size="sm">
        <Link href="/" aria-label="New debate" title="New debate">
          <Label />
        </Link>
      </Button>
    );
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="sm" aria-label="New debate" title="New debate">
          <Label />
        </Button>
      </AlertDialogTrigger>
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
          <AlertDialogAction variant="destructive" onClick={() => router.push("/")}>
            Leave debate
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

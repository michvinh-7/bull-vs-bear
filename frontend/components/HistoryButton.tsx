import Link from "next/link";
import { History } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HistoryButton() {
  return (
    <Button asChild variant="ghost" size="sm">
      <Link href="/history" aria-label="Past debates" title="Past debates">
        <History />
        <span className="hidden sm:inline">History</span>
      </Link>
    </Button>
  );
}

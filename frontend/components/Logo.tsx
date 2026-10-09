import Link from "next/link";
import { TrendingUp } from "lucide-react";

export default function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="grid size-9 place-items-center rounded-lg border bg-card">
        <TrendingUp className="size-4" />
      </span>
      <span className="leading-tight">
        <span className="block font-display font-bold">Bull vs Bear</span>
        <span className="block text-xs text-muted-foreground">AI credit committee</span>
      </span>
    </Link>
  );
}

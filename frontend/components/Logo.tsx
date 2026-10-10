import Link from "next/link";
import BrandMark from "./BrandMark";

export default function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <BrandMark size={38} />
      <span className="leading-tight">
        <span className="block font-display text-lg font-bold tracking-tight">
          <span className="text-bull">Bull</span> <span className="text-sm font-medium text-muted-foreground">vs</span>{" "}
          <span className="text-bear">Bear</span>
        </span>
        <span className="block text-xs text-muted-foreground">AI credit committee</span>
      </span>
    </Link>
  );
}

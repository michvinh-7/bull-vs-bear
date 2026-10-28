import Image from "next/image";

/** Our HackKnight 2026 result, linked to the Devpost write-up. */
export default function AwardBadge() {
  return (
    <a
      href="https://devpost.com/software/bull-vs-bear"
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2.5 rounded-full border bg-card/70 py-1 pr-4 pl-1.5 text-xs transition sm:text-sm hover:ring-2 hover:ring-foreground/15"
    >
      <Image src="/hackknight.png" alt="HackKnight logo" width={28} height={28} />
      <span>
        <span className="font-semibold">2nd place</span>
        <span className="text-muted-foreground"> · Finance Track · HackKnight 2026</span>
      </span>
    </a>
  );
}

import Link from "next/link";

export default function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="grid h-9 w-9 place-items-center rounded-lg border border-line bg-panel">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 17l6-6 4 4 8-8" />
          <path d="M15 7h6v6" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className="block font-display font-bold">Bull vs Bear</span>
        <span className="block text-xs text-neutral-400">AI credit committee</span>
      </span>
    </Link>
  );
}

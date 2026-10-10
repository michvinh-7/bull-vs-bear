import { useId } from "react";

/**
 * The Bull vs Bear mark: a badge split bull-blue / bear-orange, with a bull's horn
 * and a bear's ear, and a price line rising on the bull side and falling on the bear side.
 * Same artwork as app/icon.svg and public/logo.svg.
 */
export default function BrandMark({ size = 36, className }: { size?: number; className?: string }) {
  const clip = useId(); // unique per instance so several marks can share a page
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={className} role="img" aria-label="Bull vs Bear">
      <defs>
        <clipPath id={clip}>
          <rect x="6" y="14" width="52" height="44" rx="13" />
        </clipPath>
      </defs>
      <path d="M10 22 C 0 18, 0 6, 10 2 C 6 8, 9 13, 21 14 Z" fill="#e9c48a" />
      <circle cx="49" cy="15" r="8" fill="#f0a04b" />
      <circle cx="49" cy="15" r="3.6" fill="#0d1014" opacity="0.35" />
      <g clipPath={`url(#${clip})`}>
        <rect width="64" height="64" fill="#f0a04b" />
        <path d="M0 0 H40 L24 64 H0 Z" fill="#4f8ff7" />
      </g>
      <path d="M13 46 L23 33 L31 39 L41 28 L51 44" fill="none" stroke="#fff" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

import { cn } from "@/lib/utils";
import type { Side } from "@/lib/types";

/**
 * Original flat-style mascots (drawn for this project, no stock art).
 * While `speaking`, the head bobs and the mouth moves.
 */
export default function Mascot({ side, speaking = false, size = 48, className }: { side: Side; speaking?: boolean; size?: number; className?: string }) {
  return (
    <span
      className={cn("inline-block shrink-0", className)}
      style={{ width: size, height: size, animation: speaking ? "bob 0.6s ease-in-out infinite" : undefined }}
      aria-hidden
    >
      {side === "bull" ? <Bull speaking={speaking} /> : <Bear speaking={speaking} />}
    </span>
  );
}

const talk = (speaking: boolean) =>
  speaking ? { animation: "talk 0.28s ease-in-out infinite alternate", transformOrigin: "center", transformBox: "fill-box" as const } : undefined;

function Bull({ speaking }: { speaking: boolean }) {
  const line = "#5a3a22";
  return (
    <svg viewBox="0 0 100 100" className="size-full overflow-visible">
      <defs>
        <clipPath id="bull-head">
          <ellipse cx="50" cy="54" rx="30" ry="29" />
        </clipPath>
      </defs>
      {/* horns */}
      <path d="M33 33 C 22 27, 19 15, 25 6 C 29 16, 35 22, 43 26 Z" fill="#c98a4b" stroke={line} strokeWidth="3" strokeLinejoin="round" />
      <path d="M67 33 C 78 27, 81 15, 75 6 C 71 16, 65 22, 57 26 Z" fill="#c98a4b" stroke={line} strokeWidth="3" strokeLinejoin="round" />
      {/* ears */}
      <g transform="rotate(-18 19 47)">
        <ellipse cx="19" cy="47" rx="14" ry="8" fill="#e8ad62" stroke={line} strokeWidth="3" />
        <ellipse cx="20" cy="47" rx="8" ry="4" fill="#f4a9a4" />
      </g>
      <g transform="rotate(18 81 47)">
        <ellipse cx="81" cy="47" rx="14" ry="8" fill="#e8ad62" stroke={line} strokeWidth="3" />
        <ellipse cx="80" cy="47" rx="8" ry="4" fill="#f4a9a4" />
      </g>
      {/* head with patches */}
      <ellipse cx="50" cy="54" rx="30" ry="29" fill="#f2c879" />
      <g clipPath="url(#bull-head)">
        <path d="M14 20 C 30 22, 42 34, 40 48 C 36 58, 22 60, 14 56 Z" fill="#b8804a" />
        <ellipse cx="50" cy="34" rx="9" ry="16" fill="#fff8ec" />
      </g>
      <ellipse cx="50" cy="54" rx="30" ry="29" fill="none" stroke={line} strokeWidth="3" />
      {/* eyes + blush */}
      <circle cx="38" cy="50" r="4.2" fill="#3b2416" />
      <circle cx="62" cy="50" r="4.2" fill="#3b2416" />
      <circle cx="39.4" cy="48.6" r="1.4" fill="#fff" />
      <circle cx="63.4" cy="48.6" r="1.4" fill="#fff" />
      <circle cx="28" cy="61" r="4" fill="#f08f86" opacity="0.55" />
      <circle cx="72" cy="61" r="4" fill="#f08f86" opacity="0.55" />
      {/* muzzle */}
      <ellipse cx="50" cy="68" rx="17" ry="11.5" fill="#f6b6b1" stroke={line} strokeWidth="3" />
      <ellipse cx="44" cy="66" rx="2.4" ry="3" fill="#c9706d" />
      <ellipse cx="56" cy="66" rx="2.4" ry="3" fill="#c9706d" />
      <ellipse cx="50" cy="74" rx="4" ry="1.8" fill="#8a3f3c" style={talk(speaking)} />
    </svg>
  );
}

function Bear({ speaking }: { speaking: boolean }) {
  const line = "#4a2c17";
  return (
    <svg viewBox="0 0 100 100" className="size-full overflow-visible">
      {/* ears */}
      <circle cx="25" cy="27" r="13" fill="#91603a" stroke={line} strokeWidth="3" />
      <circle cx="75" cy="27" r="13" fill="#91603a" stroke={line} strokeWidth="3" />
      <circle cx="26" cy="28" r="7" fill="#cfa985" />
      <circle cx="74" cy="28" r="7" fill="#cfa985" />
      {/* head */}
      <ellipse cx="50" cy="55" rx="34" ry="31" fill="#91603a" stroke={line} strokeWidth="3" />
      {/* eyes */}
      <circle cx="37" cy="49" r="4.4" fill="#26160c" />
      <circle cx="63" cy="49" r="4.4" fill="#26160c" />
      <circle cx="38.5" cy="47.5" r="1.5" fill="#fff" />
      <circle cx="64.5" cy="47.5" r="1.5" fill="#fff" />
      {/* muzzle */}
      <ellipse cx="50" cy="66" rx="15.5" ry="12" fill="#cfa985" />
      <ellipse cx="50" cy="60.5" rx="6" ry="4.4" fill="#26160c" />
      <path d="M50 65 L50 69" stroke="#26160c" strokeWidth="2" strokeLinecap="round" />
      <ellipse cx="50" cy="72" rx="4.5" ry="2" fill="#5a2f1f" style={talk(speaking)} />
    </svg>
  );
}

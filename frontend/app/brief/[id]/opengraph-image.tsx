import { ImageResponse } from "next/og";
import { claimCounts } from "@/lib/briefExport";
import { loadDebateOnServer } from "@/lib/serverDebate";

// The card LinkedIn, Devpost, Slack and iMessage show for a shared brief link.
export const alt = "Bull vs Bear committee brief";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const C = {
  bg: "#0b0f15",
  panel: "#141a23",
  border: "#232b37",
  text: "#f3f5f8",
  muted: "#97a0b0",
  bull: "#5b8cff",
  bear: "#f0954a",
  verified: "#3fbf6f",
  contested: "#e3b341",
  unsupported: "#f26b6b",
};

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const debate = await loadDebateOnServer(id);
  const sheet = debate?.fact_sheet;
  const counts = debate ? claimCounts(debate) : null;
  const company = sheet?.company ?? debate?.ticker ?? "An AI credit committee";
  const topic = debate?.brief?.disputed[0]?.topic;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px 72px",
          background: C.bg,
          backgroundImage: `radial-gradient(circle at 0% 0%, ${C.bull}33, transparent 45%), radial-gradient(circle at 100% 100%, ${C.bear}33, transparent 45%)`,
          color: C.text,
          fontFamily: "sans-serif",
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, fontSize: 40, fontWeight: 700 }}>
            <span style={{ color: C.bull }}>Bull</span>
            <span style={{ color: C.muted, fontSize: 26, fontWeight: 500 }}>vs</span>
            <span style={{ color: C.bear }}>Bear</span>
          </div>
          <span style={{ color: C.muted, fontSize: 22, letterSpacing: 3 }}>AI CREDIT COMMITTEE</span>
        </div>

        {/* Company */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <span style={{ color: C.muted, fontSize: 28 }}>Committee brief</span>
          <span
            style={{
              fontSize: company.length > 28 ? 64 : 80,
              fontWeight: 700,
              lineHeight: 1.05,
              letterSpacing: -2,
              display: "block",
              lineClamp: 2,
            }}
          >
            {company}
          </span>
          {sheet && (
            <span style={{ color: C.muted, fontSize: 28 }}>
              {sheet.ticker} · figures as of {sheet.as_of}
            </span>
          )}
        </div>

        {/* Claims and the main disagreement */}
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {counts && (
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <span style={{ fontSize: 26, color: C.muted }}>{counts.total} claims checked</span>
              <Pill n={counts.verified} label="verified" color={C.verified} />
              <Pill n={counts.contested} label="contested" color={C.contested} />
              <Pill n={counts.unsupported} label="unsupported" color={C.unsupported} />
            </div>
          )}
          <span style={{ fontSize: 26, color: C.muted, display: "block", lineClamp: 1 }}>
            {topic ? `Main disagreement: ${topic}` : "Most AI tells you what to think; ours shows you what to check."}
          </span>
        </div>
      </div>
    ),
    size,
  );
}

function Pill({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 18px",
        borderRadius: 999,
        border: `2px solid ${color}88`,
        background: `${color}1f`,
        fontSize: 26,
      }}
    >
      <span style={{ fontWeight: 700 }}>{n}</span>
      <span style={{ color }}>{label}</span>
    </div>
  );
}

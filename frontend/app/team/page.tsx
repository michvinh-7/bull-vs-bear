import type { Metadata } from "next";
import AwardBadge from "@/components/AwardBadge";
import Logo from "@/components/Logo";
import NewDebateButton from "@/components/NewDebateButton";
import TeamAvatar from "@/components/TeamAvatar";
import { ThemeToggle } from "@/components/theme";

export const metadata: Metadata = { title: "Team · Bull vs Bear" };

// Photos go in public/team/ under these names; until then each card shows initials.
const TEAM = [
  {
    name: "Michael Nguyen",
    title: "Full-stack engineer",
    areas: ["Frontend", "System design", "Data layer", "Cost tracking"],
    photo: "/team/michael.jpg",
    linkedin: "https://www.linkedin.com/in/michael-vinh-nguyen/",
  },
  {
    name: "Alanna Wong",
    title: "Data & credit engineer",
    areas: ["SEC data pipeline", "Credit metrics", "Fact-checker"],
    photo: "/team/alanna.jpg",
    linkedin: "https://www.linkedin.com/in/alanna-wong-87a75213a/",
  },
  {
    name: "Fahim Taleb",
    title: "AI & backend engineer",
    areas: ["AI agents", "Guardrails", "Debate engine", "Voice", "Supabase"],
    photo: "/team/fahim.jpg",
    linkedin: "https://www.linkedin.com/in/fahim-taleb-4395ba31a/",
  },
];

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="size-3.5 fill-current">
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z" />
    </svg>
  );
}

export default function TeamPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Same bull-blue and bear-orange glows as the homepage hero */}
      <div aria-hidden className="pointer-events-none absolute -top-40 -left-40 size-[32rem] rounded-full bg-bull/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -top-24 -right-40 size-[28rem] rounded-full bg-bear/15 blur-3xl" />

      <main className="relative mx-auto flex max-w-5xl flex-col gap-14 px-4 pt-6 pb-20">
        <header className="flex items-center justify-between gap-3">
          <Logo />
          <div className="flex items-center gap-1">
            <NewDebateButton />
            <ThemeToggle />
          </div>
        </header>

        <section className="flex flex-col items-center gap-5 text-center">
          <AwardBadge />
          <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
            The team behind{" "}
            <span className="bg-linear-to-r from-bull to-bear bg-clip-text whitespace-nowrap text-transparent">Bull vs Bear</span>
          </h1>
          <p className="max-w-xl text-muted-foreground">
            Three engineers who built an AI credit committee in a weekend at HackKnight 2026.
          </p>
        </section>

        <ul className="grid gap-5 sm:grid-cols-3">
          {TEAM.map((p) => (
            <li
              key={p.name}
              className="group flex flex-col items-center gap-5 rounded-2xl border bg-card/60 p-6 text-center backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-foreground/20 hover:shadow-xl"
            >
              <a
                href={p.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${p.name} on LinkedIn`}
                className="rounded-full bg-linear-to-br from-bull to-bear p-[3px] transition duration-300 group-hover:scale-[1.03]"
              >
                <span className="block rounded-full bg-card p-1">
                  <TeamAvatar photo={p.photo} name={p.name} />
                </span>
              </a>

              <div className="flex flex-col gap-1">
                <h2 className="font-display text-lg font-semibold">{p.name}</h2>
                <p className="text-sm text-muted-foreground">{p.title}</p>
              </div>

              <ul className="flex flex-wrap justify-center gap-1.5" aria-label="Worked on">
                {p.areas.map((a) => (
                  <li key={a} className="rounded-full border bg-muted/50 px-2.5 py-0.5 text-xs text-muted-foreground">
                    {a}
                  </li>
                ))}
              </ul>

              <a
                href={p.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground transition hover:border-foreground/30 hover:text-foreground"
              >
                <LinkedInIcon />
                LinkedIn
              </a>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}

import type { Metadata } from "next";
import AwardBadge from "@/components/AwardBadge";
import Logo from "@/components/Logo";
import NewDebateButton from "@/components/NewDebateButton";
import TeamAvatar from "@/components/TeamAvatar";
import { ThemeToggle } from "@/components/theme";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = { title: "Team · Bull vs Bear" };

// Photos go in public/team/ under these names; until then each card shows initials.
const TEAM = [
  {
    name: "Michael Nguyen",
    role: "Full-stack: frontend, system design, data layer and cost tracking",
    photo: "/team/michael.jpg",
    linkedin: "https://www.linkedin.com/in/michael-vinh-nguyen/",
  },
  {
    name: "Alanna Wong",
    role: "SEC data pipeline, credit metrics and fact-checker",
    photo: "/team/alanna.jpg",
    linkedin: "https://www.linkedin.com/in/alanna-wong-87a75213a/",
  },
  {
    name: "Fahim Taleb",
    role: "AI agents, guardrails, debate engine, voice and Supabase",
    photo: "/team/fahim.jpg",
    linkedin: "https://www.linkedin.com/in/fahim-taleb-4395ba31a/",
  },
];

export default function TeamPage() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-10 px-4 pt-5 pb-16">
      <header className="flex items-center justify-between gap-3">
        <Logo />
        <div className="flex items-center gap-1">
          <NewDebateButton />
          <ThemeToggle />
        </div>
      </header>

      <section className="flex flex-col items-center gap-4 text-center">
        <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">The team</h1>
        <p className="max-w-xl text-muted-foreground">
          Bull vs Bear was built at HackKnight 2026. Click a photo to find us on LinkedIn.
        </p>
        <AwardBadge />
      </section>

      <ul className="grid gap-4 sm:grid-cols-3">
        {TEAM.map((p) => (
          <li key={p.name}>
            <Card className="h-full">
              <CardContent className="flex flex-col items-center gap-3 pt-2 text-center">
                <a
                  href={p.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${p.name} on LinkedIn`}
                  className="rounded-full transition hover:ring-4 hover:ring-bull/30"
                >
                  <TeamAvatar photo={p.photo} name={p.name} />
                </a>
                <div>
                  <div className="font-semibold">{p.name}</div>
                  <div className="text-sm text-muted-foreground">{p.role}</div>
                </div>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}

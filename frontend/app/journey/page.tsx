import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Building2, ChevronDown, GraduationCap, Mail } from "lucide-react";
import AwardBadge from "@/components/AwardBadge";
import SiteHeader from "@/components/SiteHeader";
import TeamAvatar from "@/components/TeamAvatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "Journey · Bull vs Bear" };

const CONTACT = `mailto:michvinh@gmail.com?subject=${encodeURIComponent("Bull vs Bear: getting in touch")}`;

const TEAM = [
  { name: "Michael Nguyen", photo: "/team/michael.jpg" },
  { name: "Alanna Wong", photo: "/team/alanna.jpg" },
  { name: "Fahim Taleb", photo: "/team/fahim.jpg" },
];

const BUILT = [
  ["Grounded research", "A fact sheet from SEC EDGAR filings and recent news. Code checks every quote against the source and computes every metric, so the AI never invents a number."],
  ["Two-sided debate", "One model tends to argue toward one conclusion, so two Gemini agents debate instead: the Bull argues the debt is sound, the Bear argues it’s riskier than it looks."],
  ["Independent fact-check", "A separate DeBERTa NLI model labels each claim verified, contested or unsupported."],
  ["Moderated brief", "A moderator challenges flagged claims, you can ask your own questions, and every session ends with what both sides agreed on and disputed."],
] as const;

export default function JourneyPage() {
  return (
    <div className="relative min-h-screen overflow-clip">
      <SiteHeader />
      {/* Same bull-blue and bear-orange glows as the homepage hero */}
      <div aria-hidden className="pointer-events-none absolute -top-40 -left-40 size-[32rem] rounded-full bg-bull/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -top-24 -right-40 size-[28rem] rounded-full bg-bear/15 blur-3xl" />

      <main className="relative mx-auto flex max-w-4xl flex-col gap-12 px-4 pt-14 pb-16">
        <section className="flex flex-col items-center gap-4 text-center">
          <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
            Our <span className="bg-linear-to-r from-bull to-bear bg-clip-text text-transparent">journey</span>
          </h1>
          <p className="max-w-xl text-muted-foreground">
            What we’ve built, where we’ve shown it, and what we’ve learned along the way. Click an entry to read it.
          </p>
        </section>

        {/* Entries, newest first. Each one opens to the full story. */}
        <ol className="border-t">
          <li>
            <details className="group border-b">
              <summary className="flex cursor-pointer list-none items-center gap-4 py-6 [&::-webkit-details-marker]:hidden">
                <span className="grid size-14 shrink-0 place-items-center rounded-lg border bg-card">
                  <Image src="/hackknight.png" alt="" width={36} height={36} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
                    <span className="text-bull">Entry 01</span> · Oct 2026 · HackKnight 2026
                  </p>
                  <h2 className="mt-1 font-display text-xl font-bold tracking-tight transition-colors group-hover:text-bull sm:text-2xl">
                    2nd place in the Finance Track
                  </h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    The weekend Bull vs Bear was born.
                  </p>
                </div>
                <span className="grid size-9 shrink-0 place-items-center rounded-full border text-muted-foreground transition-colors group-hover:text-foreground">
                  <ChevronDown className="size-4 transition-transform duration-200 group-open:rotate-180" />
                </span>
              </summary>

              <article className="flex flex-col gap-10 pb-12 sm:pl-[72px]">
                <figure className="overflow-hidden rounded-xl border bg-card p-1.5">
                  <Image
                    src="/journey/hackknight-stage.webp"
                    alt="The Bull vs Bear team on stage at HackKnight 2026 in front of a screen reading “2nd: BullVsBear”"
                    width={1600}
                    height={1068}
                    sizes="(min-width: 896px) 820px, 92vw"
                    className="w-full rounded-lg"
                  />
                </figure>

                <div className="flex flex-col gap-4 text-muted-foreground">
                  <p className="text-lg text-foreground">
                    We placed 2nd in the Finance Track at HackKnight 2026 with Bull vs Bear, an AI credit committee that
                    helps you figure out whether a company’s debt is actually safe.
                  </p>
                  <p>
                    Answering that question usually means digging through dense SEC filings by hand, which is slow and
                    error-prone. We wanted to automate the research without handing over the decision. Bull vs Bear never
                    picks a winner: it lays out both sides, ties every claim to its source, and lets you make the call.
                  </p>
                  <p>
                    We came to meet new people and build something we’d be proud of, and we left with a working product, a
                    live demo and a podium finish.
                  </p>
                  <div>
                    <AwardBadge />
                  </div>
                </div>

                <section className="flex flex-col gap-4">
                  <h3 className="font-display text-lg font-bold">What we built in one weekend</h3>
                  <ol className="grid gap-3 sm:grid-cols-2">
                    {BUILT.map(([title, text], i) => (
                      <li key={title}>
                        <Card className="h-full">
                          <CardHeader>
                            <span className="grid size-7 place-items-center rounded-full bg-muted font-mono text-xs">{i + 1}</span>
                            <CardTitle className="mt-2">{title}</CardTitle>
                          </CardHeader>
                          <CardContent className="text-sm text-muted-foreground">{text}</CardContent>
                        </Card>
                      </li>
                    ))}
                  </ol>
                </section>

                <div className="grid gap-4 sm:grid-cols-2">
                  <figure className="flex flex-col gap-2">
                    <Image
                      src="/journey/hackknight-team.webp"
                      alt="Michael Nguyen, Alanna Wong and Fahim Taleb in front of the HackKnight 2026 backdrop"
                      width={1600}
                      height={1067}
                      sizes="(min-width: 640px) 400px, 92vw"
                      className="aspect-[4/3] w-full rounded-lg border object-cover"
                    />
                    <figcaption className="text-xs text-muted-foreground">The team at HackKnight 2026</figcaption>
                  </figure>
                  <figure className="flex flex-col gap-2">
                    <Image
                      src="/journey/hackknight-stage-wide.webp"
                      alt="The HackKnight 2026 awards ceremony, with “2nd: BullVsBear” on the projector screen"
                      width={1600}
                      height={1200}
                      sizes="(min-width: 640px) 400px, 92vw"
                      className="aspect-[4/3] w-full rounded-lg border object-cover"
                    />
                    <figcaption className="text-xs text-muted-foreground">The awards ceremony</figcaption>
                  </figure>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-card p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex -space-x-3">
                      {TEAM.map((p) => (
                        <span key={p.name} className="rounded-full ring-2 ring-card [&_img]:size-10 [&>span]:size-10 [&>span]:text-sm">
                          <TeamAvatar photo={p.photo} name={p.name} />
                        </span>
                      ))}
                    </div>
                    <p className="text-sm">
                      Built by <span className="font-medium">Michael Nguyen, Alanna Wong and Fahim Taleb</span>
                    </p>
                  </div>
                  <Button asChild variant="outline" size="sm">
                    <Link href="/team">
                      Meet the team <ArrowRight />
                    </Link>
                  </Button>
                </div>

                <p className="text-sm text-muted-foreground">
                  Thank you to the HackKnight team, Code for All QC and Major League Hacking for putting together such a
                  great event.
                </p>
              </article>
            </details>
          </li>
        </ol>

        {/* Open invitation */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-3 text-center">
            <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">We’re still building. Come build with us.</h2>
            <p className="max-w-xl text-muted-foreground">
              HackKnight was the start, not the finish. We’re open to hearing from anyone who wants to help take Bull vs Bear
              further.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <GraduationCap className="size-5 text-bull" />
                <CardTitle className="mt-2">Students</CardTitle>
                <CardDescription>
                  Interested in AI, finance or fact-checking? We’d love to swap ideas, team up on a future hackathon, or hear
                  your feedback after trying a debate.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <Building2 className="size-5 text-bear" />
                <CardTitle className="mt-2">Businesses</CardTitle>
                <CardDescription>
                  Exploring credit research, due diligence or explainable AI? We’re open to partnerships, pilots and
                  collaboration.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button asChild>
              <a href={CONTACT}>
                <Mail /> Get in touch
              </a>
            </Button>
            <Button asChild variant="outline">
              <Link href="/team">Find us on LinkedIn</Link>
            </Button>
          </div>
        </section>

        <footer className="border-t pt-6 text-center text-xs text-muted-foreground">
          Bull vs Bear summarizes arguments from public filings. It is not investment advice.
        </footer>
      </main>
    </div>
  );
}

import type { Metadata } from "next";
import { BookOpen, CalendarRange, FileStack, FlaskConical, Mail, ScanSearch, Tags } from "lucide-react";
import SiteHeader from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Roadmap · Bull vs Bear" };

const CONTACT = `mailto:michvinh@gmail.com?subject=${encodeURIComponent("Bull vs Bear: helping with the evaluation")}`;

/** The three versions the evaluation compares, all on the same model and the same fact sheet. */
const VERSIONS = [
  ["A", "Single model", "One AI, one prompt: assess this company’s debt from the fact sheet."],
  ["B", "Debate only", "The Bull and the Bear argue it out, with no fact-checker."],
  ["C", "Full system", "The debate plus the NLI fact-checker and the moderator."],
] as const;

const MEASURES = [
  ["Error rate", "How many claims the filing contradicts or doesn’t back up at all. The headline number."],
  ["Citation accuracy", "How often the passage a claim cites actually supports it."],
  ["Number accuracy", "Whether each version quotes the Python-computed metrics correctly. Fully objective."],
  ["Fact-checker accuracy", "How many bad claims the NLI checker catches, and how often it flags good ones."],
  ["Cost and time", "What each version costs to run per company."],
] as const;

type Status = "Up next" | "Planned" | "Later";

const FEATURES: { icon: typeof BookOpen; title: string; text: string; status: Status }[] = [
  {
    icon: CalendarRange,
    title: "Debaters cite the full maturity schedule",
    text: "The maturity wall now shows every year’s debt from the 10-K. Next, the Bull and the Bear get to quote those years directly.",
    status: "Up next",
  },
  {
    icon: FileStack,
    title: "Amended filings",
    text: "When a company files a corrected 10-K/A, use the corrected numbers instead of the original filing’s.",
    status: "Planned",
  },
  {
    icon: BookOpen,
    title: "Plain-English metric guide",
    text: "What debt-to-EBITDA, interest coverage and liquidity mean, and how each one is calculated, on one page.",
    status: "Later",
  },
];

const STATUS_STYLE: Record<Status, string> = {
  "Up next": "border-bull/40 bg-bull/10 text-bull",
  Planned: "border-border bg-muted text-foreground",
  Later: "border-border text-muted-foreground",
};

export default function RoadmapPage() {
  return (
    <div className="relative min-h-screen overflow-clip">
      <SiteHeader />
      {/* Same bull-blue and bear-orange glows as the homepage hero */}
      <div aria-hidden className="pointer-events-none absolute -top-40 -left-40 size-[32rem] rounded-full bg-bull/20 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -top-24 -right-40 size-[28rem] rounded-full bg-bear/15 blur-3xl" />

      <main className="relative mx-auto flex max-w-4xl flex-col gap-14 px-4 pt-14 pb-16">
        <section className="flex flex-col items-center gap-4 text-center">
          <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
            What’s <span className="bg-linear-to-r from-bull to-bear bg-clip-text text-transparent">next</span>
          </h1>
          <p className="max-w-xl text-muted-foreground">
            What we’re testing, what we’re building, and where you can help. Plans, not promises: they’ll change as we
            learn.
          </p>
        </section>

        {/* The evaluation */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <p className="flex items-center gap-2 font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
              <FlaskConical className="size-3.5 text-bull" /> Now testing
            </p>
            <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
              Does the debate actually make fewer mistakes?
            </h2>
            <p className="text-muted-foreground">
              We’re checking whether Bull vs Bear makes fewer false or unsupported claims than simply asking one AI. Each
              company runs through three versions, so we can see what the debate adds and what the fact-checker adds.
            </p>
          </div>

          <ol className="grid gap-3 sm:grid-cols-3">
            {VERSIONS.map(([letter, title, text]) => (
              <li key={letter}>
                <Card className="h-full">
                  <CardHeader>
                    <span className="grid size-7 place-items-center rounded-full bg-muted font-mono text-xs">{letter}</span>
                    <CardTitle className="mt-2">{title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">{text}</CardContent>
                </Card>
              </li>
            ))}
          </ol>

          <div className="grid gap-6 rounded-xl border bg-card p-5 sm:grid-cols-[1fr_1.4fr]">
            <div className="flex flex-col gap-3">
              <h3 className="flex items-center gap-2 font-display text-lg font-bold">
                <Tags className="size-4 text-bear" /> How claims are checked
              </h3>
              <p className="text-sm text-muted-foreground">
                Every output is split into single factual claims. Each claim is read against the filing passage it cites
                and labeled <span className="text-foreground">supported</span>,{" "}
                <span className="text-foreground">contradicted</span> or{" "}
                <span className="text-foreground">not found</span>. Claims are shuffled with their version hidden, so
                nobody knows which one they’re grading. No finance expertise needed: it’s careful reading.
              </p>
              <p className="text-sm text-muted-foreground">
                First a 10-company pilot, healthy, heavily indebted and struggling companies, then 20 to 30 if the
                differences hold up.
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <h3 className="flex items-center gap-2 font-display text-lg font-bold">
                <ScanSearch className="size-4 text-bull" /> What we measure
              </h3>
              <dl className="flex flex-col gap-2.5 text-sm">
                {MEASURES.map(([name, text]) => (
                  <div key={name}>
                    <dt className="font-medium">{name}</dt>
                    <dd className="text-muted-foreground">{text}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">On the list</p>
            <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">Features we’re planning</h2>
          </div>
          <ul className="border-t">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex items-start gap-4 border-b py-5">
                <span className="grid size-11 shrink-0 place-items-center rounded-lg border bg-card">
                  <f.icon className="size-5 text-muted-foreground" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <h3 className="font-display text-lg font-bold tracking-tight">{f.title}</h3>
                    <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase", STATUS_STYLE[f.status])}>
                      {f.status}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{f.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        {/* Help */}
        <section className="flex flex-col items-center gap-4 rounded-xl border bg-card p-6 text-center">
          <h2 className="font-display text-2xl font-bold tracking-tight">Want to help with the evaluation?</h2>
          <p className="max-w-xl text-muted-foreground">
            We’ll be looking for a couple of careful readers to label claims, and a finance or accounting student to review
            a handful of companies’ key risks. Annotation or research-assistant experience is a plus, not a requirement.
          </p>
          <Button asChild>
            <a href={CONTACT}>
              <Mail /> Get in touch
            </a>
          </Button>
        </section>

        <footer className="border-t pt-6 text-center text-xs text-muted-foreground">
          Bull vs Bear summarizes arguments from public filings. It is not investment advice.
        </footer>
      </main>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { startDebate } from "@/lib/api";

// TODO(Person 3): fetch GET /companies for the pre-cached demo list.
const DEMO = ["NWRC"];

export default function Home() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function go(t: string) {
    if (!t.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const id = await startDebate(t.trim());
      router.push(`/debate/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-xl flex-col gap-6 px-4 py-24">
      <div>
        <h1 className="text-3xl font-bold">Bull vs Bear</h1>
        <p className="text-neutral-400">AI credit committee</p>
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          go(ticker);
        }}
      >
        <input
          className="flex-1 rounded-lg border border-line bg-panel px-4 py-2 outline-none focus:border-neutral-500"
          placeholder="Company or ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
        />
        <button
          className="rounded-lg bg-neutral-100 px-4 py-2 font-semibold text-black disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Starting…" : "Start debate"}
        </button>
      </form>
      <div className="flex gap-2 text-sm text-neutral-400">
        Try:
        {DEMO.map((t) => (
          <button key={t} className="underline hover:text-white" onClick={() => go(t)}>
            {t}
          </button>
        ))}
      </div>
      {error && <p className="text-unsupported">{error}</p>}
    </main>
  );
}

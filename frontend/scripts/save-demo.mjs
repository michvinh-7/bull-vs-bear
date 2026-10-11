// Saves a finished debate (data + every voice clip) into public/demo/<TICKER>/ so the site
// can replay it with no backend: the stage fallback.
//
//   node scripts/save-demo.mjs <TICKER> <debate-id> [api-url]
//   npm run demo:save -- AMC bb1a1f4abade
//
// Then open /debate/demo-<TICKER> (works on the live site even if Railway is down).
import { mkdirSync, readdirSync, rmSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const [ticker, debateId, api = "https://bull-vs-bear-production.up.railway.app"] = process.argv.slice(2);
if (!ticker || !debateId) {
  console.error("usage: node scripts/save-demo.mjs <TICKER> <debate-id> [api-url]");
  process.exit(1);
}
const T = ticker.toUpperCase();
const root = new URL("../public/demo/", import.meta.url).pathname;
const dir = join(root, T);

const res = await fetch(`${api}/debates/${debateId}`);
if (!res.ok) throw new Error(`GET /debates/${debateId}: ${res.status}`);
const debate = await res.json();
if (debate.status !== "done" || !debate.brief) throw new Error(`debate ${debateId} isn't finished (status ${debate.status})`);
if (debate.ticker !== T) throw new Error(`debate ${debateId} is ${debate.ticker}, not ${T}`);

rmSync(dir, { recursive: true, force: true });
mkdirSync(dir, { recursive: true });
let bytes = 0;
for (const line of debate.lines) {
  if (!line.audio_url) continue;
  const name = `${String(line.turn).padStart(2, "0")}-${line.speaker}${line.from_user ? "-you" : ""}.mp3`;
  const clip = await fetch(line.audio_url);
  if (!clip.ok) throw new Error(`clip for turn ${line.turn}: ${clip.status}`);
  const data = Buffer.from(await clip.arrayBuffer());
  writeFileSync(join(dir, name), data);
  bytes += data.length;
  line.audio_url = `/demo/${T}/${name}`; // served by the frontend itself
}
writeFileSync(join(dir, "debate.json"), JSON.stringify({ ...debate, id: `demo-${T}`, recorded_from: debateId }, null, 2));

// Index of available recordings, read by the site.
const tickers = readdirSync(root).filter((d) => existsSync(join(root, d, "debate.json"))).sort();
const index = tickers.map((t) => {
  const d = JSON.parse(readFileSync(join(root, t, "debate.json"), "utf8"));
  return { ticker: t, company: d.fact_sheet?.company ?? t, lines: d.lines.length, recorded_from: d.recorded_from };
});
writeFileSync(join(root, "index.json"), JSON.stringify(index, null, 2));

const clips = debate.lines.filter((l) => l.audio_url).length;
console.log(`${T}: ${debate.lines.length} lines, ${clips} clips (${Math.round(bytes / 1024)} KB) -> public/demo/${T}/`);
console.log(`available recordings: ${tickers.join(", ")}`);

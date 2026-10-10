import type { Speaker } from "@/lib/types";

export const SPEAKER = {
  bull: { name: "Bull", text: "text-bull", bg: "bg-bull-bg", bar: "bg-bull", ring: "ring-bull/70", align: "self-start" },
  bear: { name: "Bear", text: "text-bear", bg: "bg-bear-bg", bar: "bg-bear", ring: "ring-bear/70", align: "self-end" },
  moderator: { name: "Portfolio manager", text: "text-mod", bg: "bg-mod-bg", bar: "bg-mod", ring: "ring-mod/70", align: "self-center text-center" },
} satisfies Record<Speaker, Record<string, string>>;

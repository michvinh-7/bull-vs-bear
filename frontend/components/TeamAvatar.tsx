"use client";

import { useState } from "react";

/** A teammate's photo from /public/team, or their initials until one is added. */
export default function TeamAvatar({ photo, name }: { photo: string; name: string }) {
  const [missing, setMissing] = useState(false);
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2);
  return missing ? (
    <span className="grid size-28 place-items-center rounded-full bg-muted font-display text-2xl font-bold text-muted-foreground">
      {initials}
    </span>
  ) : (
    // A plain <img> so a missing file falls back to initials instead of a broken image.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={photo} alt={name} onError={() => setMissing(true)} className="size-28 rounded-full object-cover" />
  );
}

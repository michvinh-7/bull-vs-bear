"use client";

/**
 * One shared audio player for the whole app.
 *
 * Browsers only allow sound after a user gesture, and iOS Safari only for an
 * <audio> element that was itself played inside a gesture. So we keep two
 * reusable elements, "unlock" both from the Start-debate click, and alternate
 * between them so the next clip can preload while the current one plays.
 */

export interface ClipCallbacks {
  onProgress: (fraction: number) => void;
  onEnd: () => void;
  onBlocked: () => void; // browser refused to play: ask the user to tap
}

export interface ClipHandle {
  pause: () => void;
  resume: () => void;
  stop: () => void;
}

let elements: HTMLAudioElement[] = [];
let next = 0;
let muted = false;

function players() {
  if (!elements.length) {
    elements = [new Audio(), new Audio()];
    elements.forEach((el) => (el.preload = "auto"));
  }
  return elements;
}

/** Call synchronously inside a click/tap handler (e.g. Start debate). */
export function unlockAudio() {
  for (const el of players()) {
    el.src = silentWav();
    el.play()
      .then(() => el.pause())
      .catch(() => {});
  }
}

export function setMuted(value: boolean) {
  muted = value;
  players().forEach((el) => (el.muted = value));
}

/** Start loading a clip on the idle element so it plays without a gap. */
export function preload(url: string | undefined) {
  if (!url) return;
  const els = players();
  if (els.some((el) => el.src.endsWith(url))) return;
  const el = els[next];
  el.src = url;
  el.load();
}

/** Plays `url`, or, if there's no audio, fakes a clip of `fallbackMs` so pacing stays the same. */
export function playClip(url: string | undefined, fallbackMs: number, cb: ClipCallbacks): ClipHandle {
  if (!url) return fakeClip(fallbackMs, cb);

  const els = players();
  const el = els.find((e) => e.src.endsWith(url)) ?? els[next];
  next = (els.indexOf(el) + 1) % els.length;
  if (!el.src.endsWith(url)) el.src = url;
  el.muted = muted;
  el.currentTime = 0;

  let raf = 0;
  let done = false;
  let fallback: ClipHandle | null = null;
  const tick = () => {
    if (el.duration) cb.onProgress(Math.min(1, el.currentTime / el.duration));
    raf = requestAnimationFrame(tick);
  };
  const finish = () => {
    if (done) return;
    done = true;
    cancelAnimationFrame(raf);
    el.onended = el.onerror = null;
    cb.onEnd();
  };
  // A broken clip shouldn't stall the debate: fall back to a fake clip.
  const failover = () => {
    if (done) return;
    done = true;
    cancelAnimationFrame(raf);
    el.onended = el.onerror = null;
    fallback = fakeClip(fallbackMs, cb);
  };

  el.onended = finish;
  el.onerror = failover;
  el.play()
    .then(() => (raf = requestAnimationFrame(tick)))
    .catch((err: DOMException) => {
      if (err.name === "NotAllowedError") {
        done = true;
        el.onended = el.onerror = null;
        cb.onBlocked();
      } else failover();
    });

  return {
    pause: () => (fallback ? fallback.pause() : el.pause()),
    resume: () => (fallback ? fallback.resume() : el.play().catch(() => {})),
    stop: () => {
      done = true;
      cancelAnimationFrame(raf);
      el.onended = el.onerror = null;
      el.pause();
      fallback?.stop();
    },
  };
}

function fakeClip(ms: number, cb: ClipCallbacks): ClipHandle {
  let elapsed = 0;
  let startedAt = performance.now();
  let raf = 0;
  let paused = false;
  const tick = (now: number) => {
    const t = elapsed + (now - startedAt);
    cb.onProgress(Math.min(1, t / ms));
    if (t >= ms) return cb.onEnd();
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return {
    pause: () => {
      if (paused) return;
      paused = true;
      elapsed += performance.now() - startedAt;
      cancelAnimationFrame(raf);
    },
    resume: () => {
      if (!paused) return;
      paused = false;
      startedAt = performance.now();
      raf = requestAnimationFrame(tick);
    },
    stop: () => cancelAnimationFrame(raf),
  };
}

/** Roughly how long a line takes to say (~160 words per minute). */
export function speakingTimeMs(text: string) {
  return Math.max(1500, text.split(/\s+/).length * 375);
}

let silent: string | null = null;
/** A 0.1 s silent WAV, built once, used to unlock the audio elements. */
function silentWav() {
  if (silent) return silent;
  const samples = 800; // 0.1 s at 8 kHz, 8-bit mono
  const buf = new Uint8Array(44 + samples);
  const view = new DataView(buf.buffer);
  const ascii = (offset: number, s: string) => [...s].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  ascii(0, "RIFF");
  view.setUint32(4, 36 + samples, true);
  ascii(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, 8000, true);
  view.setUint32(28, 8000, true);
  view.setUint16(32, 1, true);
  view.setUint16(34, 8, true);
  ascii(36, "data");
  view.setUint32(40, samples, true);
  buf.fill(128, 44); // 8-bit silence
  silent = "data:audio/wav;base64," + btoa(String.fromCharCode(...buf));
  return silent;
}

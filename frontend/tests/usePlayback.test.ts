// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { LineMessage } from "@/lib/types";

// Fake player: records every clip started and lets the test decide when it ends.
type Clip = { url?: string; fallbackMs: number; cb: { onProgress: (f: number) => void; onEnd: () => void; onBlocked: () => void }; stopped: boolean; paused: boolean };
const clips: Clip[] = [];
let playing = 0;
let maxPlaying = 0;

vi.mock("@/lib/audio", () => ({
  playClip: (url: string | undefined, fallbackMs: number, cb: Clip["cb"]) => {
    const clip: Clip = { url, fallbackMs, cb, stopped: false, paused: false };
    clips.push(clip);
    maxPlaying = Math.max(maxPlaying, ++playing);
    const end = cb.onEnd;
    clip.cb = { ...cb, onEnd: () => (playing--, end()), onBlocked: () => (playing--, cb.onBlocked()) };
    return { pause: () => (clip.paused = true), resume: () => (clip.paused = false), stop: () => (clip.stopped = true) };
  },
  preload: vi.fn(),
  setMuted: vi.fn(),
  unlockAudio: vi.fn(),
  speakingTimeMs: (t: string) => t.length * 10,
}));

const { usePlayback } = await import("@/lib/usePlayback");
const audio = await import("@/lib/audio");

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** Minimal renderHook (React Testing Library isn't installed). */
function renderHook<P, R>(hook: (p: P) => R, initial: P) {
  const result = { current: undefined as R };
  let props = initial;
  const Probe = () => ((result.current = hook(props)), null);
  const root = createRoot(document.createElement("div"));
  act(() => root.render(createElement(Probe)));
  return {
    result,
    rerender: (p: P) => {
      props = p;
      act(() => root.render(createElement(Probe)));
    },
    unmount: () => act(() => root.unmount()),
  };
}

const line = (turn: number, speaker: LineMessage["speaker"], audio_url = `/clip-${turn}.m4a`): LineMessage => ({
  turn,
  speaker,
  from_user: false,
  text: `line ${turn}`,
  claims: [],
  audio_url,
});
const advance = (ms: number) => act(() => vi.advanceTimersByTime(ms));
const endClip = (i: number) => act(() => clips[i].cb.onEnd());

beforeEach(() => {
  vi.useFakeTimers();
  clips.length = 0;
  playing = 0;
  maxPlaying = 0;
  vi.mocked(audio.unlockAudio).mockClear();
});
afterEach(() => vi.useRealTimers());

describe("usePlayback", () => {
  it("plays lines one at a time, in order, with a short gap", () => {
    const lines = [line(1, "bull"), line(2, "bear"), line(3, "moderator")];
    const { result } = renderHook(usePlayback, lines);
    advance(0);
    expect(clips.map((c) => c.url)).toEqual(["/clip-1.m4a"]);
    expect(result.current.speaker).toBe("bull");
    expect(result.current.shown).toHaveLength(1);

    advance(10_000); // a long clip: nothing else may start until it ends
    expect(clips).toHaveLength(1);

    endClip(0);
    advance(349);
    expect(clips).toHaveLength(1); // still in the gap
    advance(1);
    expect(clips.map((c) => c.url)).toEqual(["/clip-1.m4a", "/clip-2.m4a"]);
    expect(result.current.speaker).toBe("bear");

    endClip(1);
    advance(350);
    endClip(2);
    expect(result.current.finished).toBe(true);
    expect(result.current.speaker).toBeNull();
    expect(maxPlaying).toBe(1); // never two clips at once
  });

  it("doesn't start a second clip when new lines arrive mid-clip", () => {
    const { result, rerender } = renderHook(usePlayback, [line(1, "bull")]);
    advance(0);
    rerender([line(1, "bull"), line(2, "bear"), line(3, "bull")]);
    advance(5000);
    expect(clips).toHaveLength(1);
    expect(result.current.shown).toHaveLength(1);
  });

  it("waits for more lines when caught up, then continues", () => {
    const { result, rerender } = renderHook(usePlayback, [line(1, "bull")]);
    advance(0);
    endClip(0);
    advance(1000);
    expect(result.current.caughtUp).toBe(true);
    expect(result.current.finished).toBe(true); // finished = caught up; the page also waits for the brief
    rerender([line(1, "bull"), line(2, "bear")]);
    advance(350);
    expect(clips.map((c) => c.url)).toEqual(["/clip-1.m4a", "/clip-2.m4a"]);
  });

  it("uses a timed stand-in when a line has no audio", () => {
    renderHook(usePlayback, [line(1, "bull", "")]);
    advance(0);
    expect(clips[0].url).toBeUndefined();
    expect(clips[0].fallbackMs).toBe("line 1".length * 10);
  });

  it("tracks progress for the typing reveal", () => {
    const { result } = renderHook(usePlayback, [line(1, "bull")]);
    advance(0);
    act(() => clips[0].cb.onProgress(0.4));
    expect(result.current.progress).toBe(0.4);
  });

  it("pause holds the queue; resume continues it", () => {
    const { result } = renderHook(usePlayback, [line(1, "bull"), line(2, "bear")]);
    advance(0);
    act(() => result.current.togglePause());
    expect(clips[0].paused).toBe(true);
    endClip(0);
    advance(5000);
    expect(clips).toHaveLength(1); // nothing new while paused
    act(() => result.current.togglePause());
    advance(350);
    expect(clips).toHaveLength(2);
  });

  it("asks for a tap when the browser blocks sound, then retries the same line", () => {
    const { result } = renderHook(usePlayback, [line(1, "bull"), line(2, "bear")]);
    advance(0);
    act(() => clips[0].cb.onBlocked());
    expect(result.current.blocked).toBe(true);
    expect(result.current.shown).toHaveLength(0);
    advance(5000);
    expect(clips).toHaveLength(1); // stays put until the tap

    act(() => result.current.unblock());
    expect(audio.unlockAudio).toHaveBeenCalledOnce();
    advance(350);
    expect(clips.map((c) => c.url)).toEqual(["/clip-1.m4a", "/clip-1.m4a"]);
  });

  it("reports each line as played, in order, only when its clip ends", () => {
    const played: number[] = [];
    renderHook((ls: LineMessage[]) => usePlayback(ls, (t) => played.push(t)), [line(1, "bull"), line(2, "bear")]);
    advance(0);
    expect(played).toEqual([]); // still playing
    endClip(0);
    expect(played).toEqual([1]);
    advance(350);
    endClip(1);
    expect(played).toEqual([1, 2]);
  });

  it("doesn't report a line the browser refused to play", () => {
    const played: number[] = [];
    renderHook((ls: LineMessage[]) => usePlayback(ls, (t) => played.push(t)), [line(1, "bull")]);
    advance(0);
    act(() => clips[0].cb.onBlocked());
    expect(played).toEqual([]);
  });

  it("stops the current clip when the page closes", () => {
    const { unmount } = renderHook(usePlayback, [line(1, "bull")]);
    advance(0);
    unmount();
    expect(clips[0].stopped).toBe(true);
  });
});

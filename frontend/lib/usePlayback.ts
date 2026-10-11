"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { playClip, preload, setMuted as setPlayerMuted, speakingTimeMs, unlockAudio, type ClipHandle } from "./audio";
import type { LineMessage } from "./types";

const GAP_MS = 350; // silence between turns (target: under ~1.5 s)

/**
 * Turns "lines received from the server" into "lines the audience has heard".
 * Plays one clip at a time, in order; a line's bubble appears when its clip starts.
 */
export function usePlayback(lines: LineMessage[], onPlayed?: (turn: number) => void) {
  const [index, setIndex] = useState(-1); // line currently playing, or last one played
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0); // 0..1 through the current clip
  const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(false);
  const [blocked, setBlocked] = useState(false); // autoplay refused; needs a tap
  const handle = useRef<ClipHandle | null>(null);
  // Latest callback without restarting clips when the parent re-renders.
  const onPlayedRef = useRef(onPlayed);
  onPlayedRef.current = onPlayed;

  const start = useCallback(
    (i: number) => {
      const line = lines[i];
      setIndex(i);
      setPlaying(true);
      setProgress(0);
      handle.current = playClip(line.audio_url || undefined, speakingTimeMs(line.text), {
        onProgress: setProgress,
        onEnd: () => {
          setProgress(1);
          setPlaying(false);
          onPlayedRef.current?.(line.turn); // tells the server where playback is (pacing)
        },
        onBlocked: () => {
          setBlocked(true);
          setPlaying(false);
          setIndex(i - 1); // retry this line after the tap
        },
      });
    },
    [lines],
  );

  // Whenever we're idle and another line is waiting, play it after a short gap.
  useEffect(() => {
    if (playing || paused || blocked || index + 1 >= lines.length) return;
    const t = setTimeout(() => start(index + 1), index < 0 ? 0 : GAP_MS);
    return () => clearTimeout(t);
  }, [playing, paused, blocked, index, lines.length, start]);

  // Load the following clip while this one plays.
  useEffect(() => {
    preload(lines[index + 1]?.audio_url || undefined);
  }, [index, lines]);

  useEffect(
    () => () => {
      handle.current?.stop();
      setPlayerMuted(false); // the player is shared; don't leak mute into the next debate
    },
    [],
  );

  const togglePause = useCallback(() => {
    if (paused) handle.current?.resume();
    else handle.current?.pause();
    setPaused(!paused);
  }, [paused]);

  const toggleMute = useCallback(() => {
    setPlayerMuted(!muted);
    setMuted(!muted);
  }, [muted]);

  /** For the "Play debate" button shown when the browser blocked autoplay. */
  const unblock = useCallback(() => {
    unlockAudio();
    setBlocked(false);
  }, []);

  const current = playing ? lines[index] : null;
  return {
    shown: lines.slice(0, index + 1),
    current, // the line being spoken right now
    progress,
    speaker: current?.speaker ?? null,
    finished: lines.length > 0 && index === lines.length - 1 && !playing,
    caughtUp: index === lines.length - 1 && !playing, // waiting on the server for more
    paused,
    togglePause,
    muted,
    toggleMute,
    blocked,
    unblock,
  };
}

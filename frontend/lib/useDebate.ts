"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { USE_MOCK, wsUrl } from "./api";
import { mockDebate } from "./mock";
import type { CommitteeBrief, FactSheet, LineMessage, Positions, ServerMessage, Speaker } from "./types";

type Status = "connecting" | "live" | "done" | "error";

/** Connects to the debate stream (or plays mock data) and plays audio in order. */
export function useDebate(debateId: string) {
  const [factSheet, setFactSheet] = useState<FactSheet | null>(null);
  const [positions, setPositions] = useState<Positions | null>(null);
  const [lines, setLines] = useState<LineMessage[]>([]);
  const [brief, setBrief] = useState<CommitteeBrief | null>(null);
  // Who is generating the next line right now ("Bear is thinking…"); null between turns.
  const [thinking, setThinking] = useState<{ turn: number; speaker: Speaker } | null>(null);
  const [maxTurns, setMaxTurns] = useState<number | null>(null);
  const [status, setStatus] = useState<Status>("connecting");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audio = useAudioQueue();
  const enqueue = audio.enqueue;

  const handle = useCallback(
    (msg: ServerMessage) => {
      switch (msg.type) {
        case "fact_sheet":
          setFactSheet(msg.data);
          break;
        case "positions":
          setPositions(msg.data);
          break;
        case "turn_start":
          setThinking({ turn: msg.turn, speaker: msg.speaker });
          setMaxTurns(msg.max_turns);
          break;
        case "line":
          setThinking(null);
          setLines((prev) => [...prev, msg.data]);
          if (msg.data.audio_url) enqueue(msg.data.audio_url);
          break;
        case "brief":
          setBrief(msg.data);
          setStatus("done");
          break;
        case "error":
          setError(msg.message);
          setStatus("error");
          break;
      }
    },
    [enqueue],
  );

  useEffect(() => {
    if (USE_MOCK) {
      setStatus("live");
      const m = mockDebate;
      const queue: ServerMessage[] = [
        { type: "fact_sheet", data: m.fact_sheet! },
        { type: "positions", data: m.positions! },
        ...m.lines.flatMap((data): ServerMessage[] => [
          { type: "turn_start", turn: data.turn, speaker: data.speaker, max_turns: m.max_turns },
          { type: "line", data },
        ]),
        { type: "brief", data: m.brief! },
      ];
      const timers = queue.map((msg, i) => setTimeout(() => handle(msg), i * 900));
      return () => timers.forEach(clearTimeout);
    }

    const ws = new WebSocket(wsUrl(debateId));
    wsRef.current = ws;
    ws.onopen = () => setStatus("live");
    ws.onmessage = (e) => handle(JSON.parse(e.data));
    ws.onerror = () => {
      setError("Connection lost");
      setStatus("error");
    };
    return () => ws.close();
  }, [debateId, handle]);

  const interrupt = useCallback((question: string) => {
    if (USE_MOCK) {
      setLines((prev) => [
        ...prev,
        { turn: prev.length + 1, speaker: "moderator", from_user: true, text: question, claims: [], audio_url: "" },
      ]);
      return;
    }
    wsRef.current?.send(JSON.stringify({ type: "interrupt", question }));
  }, []);

  return { factSheet, positions, lines, brief, thinking, maxTurns, status, error, interrupt, audio };
}

/** Plays audio clips one after another. TODO(Person 3): pause/mute controls, preload next clip. */
function useAudioQueue() {
  const queue = useRef<string[]>([]);
  const playing = useRef(false);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const playNext = useCallback(() => {
    const url = queue.current.shift();
    if (!url) {
      playing.current = false;
      return;
    }
    playing.current = true;
    const el = new Audio(url);
    el.muted = mutedRef.current;
    el.onended = playNext;
    el.onerror = playNext;
    el.play().catch(playNext);
  }, []);

  const enqueue = useCallback(
    (url: string) => {
      queue.current.push(url);
      if (!playing.current) playNext();
    },
    [playNext],
  );

  return { enqueue, muted, setMuted };
}

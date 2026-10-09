"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { USE_MOCK, wsUrl } from "./api";
import type { CommitteeBrief, FactSheet, LineMessage, ServerMessage } from "./types";
import mockFactSheet from "./mock/fact_sheet.json";
import mockLines from "./mock/line_messages.json";
import mockBrief from "./mock/committee_brief.json";

type Status = "connecting" | "live" | "done" | "error";

/** Connects to the debate stream (or plays mock data) and plays audio in order. */
export function useDebate(debateId: string) {
  const [factSheet, setFactSheet] = useState<FactSheet | null>(null);
  const [lines, setLines] = useState<LineMessage[]>([]);
  const [brief, setBrief] = useState<CommitteeBrief | null>(null);
  const [status, setStatus] = useState<Status>("connecting");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const audio = useAudioQueue();
  const enqueue = audio.enqueue;

  const handle = useCallback(
    (msg: ServerMessage) => {
      if (msg.type === "fact_sheet") setFactSheet(msg.data);
      if (msg.type === "line") {
        setLines((prev) => [...prev, msg.data]);
        if (msg.data.audio_url) enqueue(msg.data.audio_url);
      }
      if (msg.type === "brief") {
        setBrief(msg.data);
        setStatus("done");
      }
      if (msg.type === "error") {
        setError(msg.message);
        setStatus("error");
      }
    },
    [enqueue],
  );

  useEffect(() => {
    if (USE_MOCK) {
      setStatus("live");
      const queue: ServerMessage[] = [
        { type: "fact_sheet", data: mockFactSheet as FactSheet },
        ...(mockLines as LineMessage[]).map((data) => ({ type: "line" as const, data })),
        { type: "brief", data: mockBrief as CommitteeBrief },
      ];
      const timers = queue.map((m, i) => setTimeout(() => handle(m), i * 1500));
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
        { turn: prev.length + 1, speaker: "moderator", text: question, claims: [], audio_url: "" },
      ]);
      return;
    }
    wsRef.current?.send(JSON.stringify({ type: "interrupt", question }));
  }, []);

  return { factSheet, lines, brief, status, error, interrupt, audio };
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

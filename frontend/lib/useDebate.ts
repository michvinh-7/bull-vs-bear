"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getDebate, USE_MOCK, wsUrl } from "./api";
import { mockDebate } from "./mock";
import type { CommitteeBrief, FactSheet, LineMessage, Positions, ServerMessage, Speaker } from "./types";

type Status = "connecting" | "live" | "done" | "error";

/** Connects to the debate stream (or plays mock data). Playback lives in usePlayback. */
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
  const linesRef = useRef(lines);
  linesRef.current = lines;
  // A question the user just sent, shown right away until the committee's
  // moderator line for it arrives.
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  // Replays stream a finished debate from storage; the server isn't taking questions.
  const [replay, setReplay] = useState(false);

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
          if (msg.data.from_user) setPendingQuestion(null);
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
    [],
  );

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("replay") === "1") setReplay(true);
    else if (!USE_MOCK) getDebate(debateId).then((d) => setReplay(d.status === "done")).catch(() => {});
  }, [debateId]);

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

  const interrupt = useCallback(
    (question: string) => {
      setPendingQuestion(question);
      if (USE_MOCK) {
        // Pretend the server relays it as the next moderator line.
        const turn = linesRef.current.length + 1;
        setTimeout(
          () => handle({ type: "line", data: { turn, speaker: "moderator", from_user: true, text: question, claims: [], audio_url: "" } }),
          1200,
        );
        return;
      }
      wsRef.current?.send(JSON.stringify({ type: "interrupt", question }));
    },
    [handle],
  );

  return { factSheet, positions, lines, brief, thinking, maxTurns, status, error, interrupt, pendingQuestion, replay };
}

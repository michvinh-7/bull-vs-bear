"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getDebate, USE_MOCK, wsUrl } from "./api";
import { isDemoId, loadDemo } from "./demo";
import { mockDebate } from "./mock";
import { mockModels, mockUsage } from "./mock/models";
import { addToTotals, getModel } from "./settings";
import type { CommitteeBrief, Debate, FactSheet, LineMessage, Positions, ServerMessage, Speaker, Usage } from "./types";

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
  const replayRef = useRef(replay);
  replayRef.current = replay;
  // Tokens, calls, voice characters and estimated cost so far (sent by the backend).
  const [usage, setUsage] = useState<Usage | null>(null);
  // Reopened (e.g. refreshed) mid-debate: the server replays what was said and won't continue.
  const [interrupted, setInterrupted] = useState(false);
  const usageRef = useRef<Usage | null>(null);
  // Mock runs get their own id so each one adds to the browser total.
  const runId = useRef(debateId === "mock" ? `mock-${Date.now()}` : debateId);

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
        case "interrupted":
          setInterrupted(true);
          setThinking(null);
          setStatus("done");
          break;
        case "usage":
          usageRef.current = msg.data;
          setUsage(msg.data);
          break;
        case "brief":
          setBrief(msg.data);
          setStatus("done");
          // A finished live debate adds to this browser's running total (replays cost nothing).
          if (usageRef.current && !replayRef.current) addToTotals(runId.current, usageRef.current);
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
    // Recordings (demo-<TICKER>) are replays: nobody is there to answer questions.
    if (isDemoId(debateId) || new URLSearchParams(window.location.search).get("replay") === "1") setReplay(true);
    else if (!USE_MOCK) getDebate(debateId)
        .then((d) => setReplay(d.status === "done" || d.status === "interrupted"))
        .catch(() => {});
  }, [debateId]);

  useEffect(() => {
    // Play a whole debate from data, message by message, as if it were streaming in.
    const play = (m: Debate, usageAt: (lines: number, done?: boolean) => Usage | null) => {
      setStatus("live");
      const usageMsg = (u: Usage | null): ServerMessage[] => (u ? [{ type: "usage", data: u }] : []);
      const queue: ServerMessage[] = [
        { type: "fact_sheet", data: m.fact_sheet! },
        { type: "positions", data: m.positions! },
        ...usageMsg(usageAt(0)),
        ...m.lines.flatMap((data, i): ServerMessage[] => [
          { type: "turn_start", turn: data.turn, speaker: data.speaker, max_turns: m.lines.length },
          { type: "line", data },
          ...usageMsg(usageAt(i + 1)),
        ]),
        ...usageMsg(usageAt(m.lines.length, true)),
        { type: "brief", data: m.brief! },
      ];
      return queue.map((msg, i) => setTimeout(() => handle(msg), i * 900));
    };

    // Stage fallback: a recorded real debate, served by the frontend itself (no backend).
    if (isDemoId(debateId)) {
      let timers: ReturnType<typeof setTimeout>[] = [];
      let cancelled = false;
      loadDemo(debateId)
        .then((d) => {
          if (!cancelled) timers = play(d, (_, done) => (done ? (d.usage ?? null) : null));
        })
        .catch((e) => {
          setError(e.message);
          setStatus("error");
        });
      return () => {
        cancelled = true;
        timers.forEach(clearTimeout);
      };
    }

    if (USE_MOCK) {
      const model = getModel() ?? mockModels.default;
      const timers = play(mockDebate, (n, done) => mockUsage(model, n, done));
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

  /** Line `turn` finished playing: the backend paces itself one line ahead of this. */
  const reportPlayed = useCallback((turn: number) => {
    if (USE_MOCK || replayRef.current) return; // nothing is listening
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "played", turn }));
  }, []);

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

  return { factSheet, positions, lines, brief, thinking, maxTurns, status, error, interrupt, pendingQuestion, replay, usage, reportPlayed, interrupted };
}

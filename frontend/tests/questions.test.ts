import { describe, expect, it } from "vitest";
import { closedReason, MAX_QUESTIONS, serverFinished, type QuestionState } from "@/lib/questions";

const open: QuestionState = { replay: false, done: false, serverFinished: false, asked: 0, waiting: false };

describe("closedReason", () => {
  it("is open by default", () => {
    expect(closedReason(open)).toBeNull();
  });
  it("closes when the debate was interrupted (reopened mid-debate), before anything else", () => {
    expect(closedReason({ ...open, interrupted: true, replay: true, asked: 9 })).toMatch(/interrupted/);
  });
  it("closes during a replay, whatever else is true", () => {
    expect(closedReason({ ...open, replay: true, done: true, asked: 9 })).toMatch(/replay/);
  });
  it("closes when the debate is done", () => {
    expect(closedReason({ ...open, done: true, serverFinished: true })).toBe("The debate has ended");
  });
  it("closes when the server stopped taking questions", () => {
    expect(closedReason({ ...open, serverFinished: true })).toMatch(/finished taking questions/);
  });
  it("closes at the question limit, not before", () => {
    expect(closedReason({ ...open, asked: MAX_QUESTIONS - 1 })).toBeNull();
    expect(closedReason({ ...open, asked: MAX_QUESTIONS })).toMatch(/limit reached/);
  });
  it("waits while a question is in flight", () => {
    expect(closedReason({ ...open, waiting: true })).toMatch(/Waiting/);
  });
  it("prefers the limit message over waiting", () => {
    expect(closedReason({ ...open, waiting: true, asked: MAX_QUESTIONS })).toMatch(/limit reached/);
  });
});

describe("serverFinished", () => {
  it("is false until the brief arrives, even when every planned line is in", () => {
    // The backend keeps taking questions until the last line is heard (pacing), then sends the brief.
    expect(serverFinished({ brief: false })).toBe(false);
  });
  it("is true once the brief arrives", () => {
    expect(serverFinished({ brief: true })).toBe(true);
  });
});

// Must match MAX_INTERRUPTS on the backend (backend/app/config.py).
export const MAX_QUESTIONS = 3;

export interface QuestionState {
  replay: boolean; // streaming a finished debate from storage
  done: boolean; // last clip played and the brief is in
  serverFinished: boolean; // backend stopped taking questions (it writes ahead of the audio)
  asked: number; // questions sent so far, including one still in flight
  waiting: boolean; // a question is sent but not yet heard
}

/** Why the interrupt bar is closed, or null if the user can ask. First reason wins. */
export function closedReason(s: QuestionState): string | null {
  if (s.replay) return "This is a replay, so questions are off";
  if (s.done) return "The debate has ended";
  if (s.serverFinished) return "The committee has finished taking questions";
  if (s.asked >= MAX_QUESTIONS) return `Question limit reached (${MAX_QUESTIONS} per debate)`;
  if (s.waiting) return "Waiting for the committee…";
  return null;
}

/** The backend has written its last line once the brief arrives, or every planned turn is in. */
export function serverFinished(opts: { brief: boolean; lines: number; maxTurns: number | null; thinking: boolean }) {
  return opts.brief || (opts.maxTurns !== null && opts.lines >= opts.maxTurns && !opts.thinking);
}

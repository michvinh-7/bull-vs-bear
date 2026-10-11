// Must match MAX_INTERRUPTS on the backend (backend/app/config.py).
export const MAX_QUESTIONS = 3;

export interface QuestionState {
  replay: boolean; // streaming a finished debate from storage
  interrupted?: boolean; // the debate was cut off (a refresh mid-debate) and can't continue
  done: boolean; // last clip played and the brief is in
  serverFinished: boolean; // backend stopped taking questions (it writes ahead of the audio)
  asked: number; // questions sent so far, including one still in flight
  waiting: boolean; // a question is sent but not yet heard
}

/** Why the interrupt bar is closed, or null if the user can ask. First reason wins. */
export function closedReason(s: QuestionState): string | null {
  if (s.interrupted) return "This debate was interrupted, so questions are off";
  if (s.replay) return "This is a replay, so questions are off";
  if (s.done) return "The debate has ended";
  if (s.serverFinished) return "The committee has finished taking questions";
  if (s.asked >= MAX_QUESTIONS) return `Question limit reached (${MAX_QUESTIONS} per debate)`;
  if (s.waiting) return "Waiting for the committee…";
  return null;
}

/**
 * The backend stops taking questions when it sends the brief. It paces itself to
 * the audio and keeps taking questions until the last line has been heard, so
 * "every planned line has arrived" is not the end; the brief is.
 */
export function serverFinished(opts: { brief: boolean }) {
  return opts.brief;
}

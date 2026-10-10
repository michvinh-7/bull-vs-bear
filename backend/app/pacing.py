"""Keeps the debate one line ahead of what the listener is hearing. Owner: Person 2.

Gemini writes a line in ~2 s; the line takes ~15 s to play. Without pacing the
server finishes the whole debate in ~20 s and hangs up, so an interrupt a
minute in goes nowhere. With pacing, the next line is written while the
current one plays, and a question is answered right after it.

Where playback is:
  - If the client sends {"type": "played", "turn": n} when line n finishes,
    that's used (exact).
  - Otherwise it's estimated from each line's length at speaking pace.
  - A line also counts as finished once its estimate is GRACE seconds overdue,
    so a client that stops reporting (tab in background) can't stall the debate.
"""
import asyncio
import time

WORDS_PER_SECOND = 2.6  # ElevenLabs speaking pace
GAP_SECONDS = 0.6  # pause between clips on the client
GRACE_SECONDS = 20.0


def speaking_seconds(text: str) -> float:
    return len(text.split()) / WORDS_PER_SECOND + GAP_SECONDS


class Pacer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.finish_at: dict[int, float] = {}  # turn -> estimated end of playback
        self.played_turn = 0  # highest turn the client says has finished
        self.client_reports = False

    def sent(self, turn: int, text: str) -> None:
        """A line went to the client; it plays after everything before it."""
        start = max([self.clock(), *self.finish_at.values()])
        self.finish_at[turn] = start + speaking_seconds(text)

    def played(self, turn: int) -> None:
        self.client_reports = True
        self.played_turn = max(self.played_turn, turn)

    def unfinished(self) -> int:
        """Lines sent that the listener hasn't finished hearing."""
        now = self.clock()

        def done(turn: int, end: float) -> bool:
            if self.client_reports:
                return turn <= self.played_turn or now > end + GRACE_SECONDS
            return now >= end

        return sum(not done(t, end) for t, end in self.finish_at.items())

    async def wait(self, at_most: int, wake: asyncio.Queue | None = None, poll: float = 0.2) -> None:
        """Wait until at most `at_most` lines are unheard, or a question arrives on `wake`."""
        while self.unfinished() > at_most and (wake is None or wake.empty()):
            await asyncio.sleep(poll)

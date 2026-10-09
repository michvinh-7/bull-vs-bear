"""Hugging Face fact-checking. Owner: Person 1.

Reads a claim and its cited passage and decides if the passage backs it up.
Independent of Gemini, so it's not the AI grading its own work.

Suggested approach: an NLI model (e.g. cross-encoder/nli-deberta-v3-base or
facebook/bart-large-mnli) with premise=passage, hypothesis=claim.
  entailment    -> verified
  contradiction -> contested
  neutral       -> unsupported
"""
from .schemas import Claim


def check_claim(claim: Claim) -> Claim:
    # Ground rule: no citation means Unsupported.
    if not claim.source or not claim.passage:
        claim.label = "unsupported"
        return claim
    # TODO(Person 1): call the NLI model here.
    return claim


def check_claims(claims: list[Claim]) -> list[Claim]:
    return [check_claim(c) for c in claims]

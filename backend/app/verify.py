"""Hugging Face fact-checking. Owner: Person 1.

Reads a claim and the excerpt of the source it cites and decides if the excerpt
backs it up. The excerpt comes from the fact sheet, never from the debater, and
the model is independent of Gemini, so it's not the AI grading its own work.

Suggested approach: an NLI model (e.g. cross-encoder/nli-deberta-v3-base or
facebook/bart-large-mnli) with premise=excerpt, hypothesis=claim.
  entailment    -> verified
  contradiction -> contested
  neutral       -> unsupported
"""
from .schemas import Claim, FactSheet


def check_claim(claim: Claim, fact_sheet: FactSheet) -> Claim:
    source = fact_sheet.source(claim.source_id)
    # Ground rule: no citation (or a made-up one) means Unsupported.
    if source is None:
        claim.source_id = None
        claim.label = "unsupported"
        return claim
    # TODO(Person 1): run NLI on (source.excerpt, claim.text) and set claim.label.
    return claim


def check_claims(claims: list[Claim], fact_sheet: FactSheet) -> list[Claim]:
    return [check_claim(c, fact_sheet) for c in claims]

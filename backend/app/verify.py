"""Hugging Face fact-checking. Owner: Person 1.

Reads a claim and the excerpt of the source it cites and decides if the excerpt
backs it up. The excerpt comes from the fact sheet, never from the debater, and
the model is independent of Gemini, so it's not the AI grading its own work.

Uses an NLI model (MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli) with
  premise=excerpt, hypothesis=claim.
  entailment    -> verified
  contradiction -> contested
  neutral       -> unsupported
"""
from functools import lru_cache

from .agents import _number_text, numbers, show_metric
from .schemas import Claim, FactSheet

# Runs locally (hosted inference needs paid credits).
# First call downloads several hundred MB of weights into ~/.cache/huggingface.
NLI_MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"

LABELS = {
    "entailment": "verified",
    "contradiction": "contested",
    "neutral": "unsupported",
}


@lru_cache(maxsize=1)
def _load():
    # Imported here so the server starts fast and tests don't need torch.
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL)
    model.eval()
    return tokenizer, model


def nli(premise: str, hypothesis: str) -> str:
    """Return the model's top label: entailment, contradiction or neutral."""
    import torch

    tokenizer, model = _load()
    inputs = tokenizer(premise, hypothesis, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits[0]
    return model.config.id2label[int(logits.argmax())].lower()


def check_claim(claim: Claim, fact_sheet: FactSheet) -> Claim:
    source = fact_sheet.source(claim.source_id)
    # Ground rule: no citation (or a made-up one) means Unsupported.
    if source is None:
        claim.source_id = None
        claim.label = "unsupported"
        return claim
    # premise = the filing excerpt, hypothesis = what the debater said. Excerpts say "we" and
    # "the company", so the premise names the company or the model can't tie a claim about
    # Verizon to them. Metrics computed from this source are added too: the model can't
    # work out "13.6x leverage" from the debt and EBITDA figures on its own.
    # Errors are raised, not hidden: main.py catches them and leaves labels "pending".
    computed = [
        f"{m.label} was {show_metric(m.value, m.unit)} ({m.formula})."
        for m in fact_sheet.metrics
        if source.id in m.source_ids
    ]
    premise = " ".join([f"From {fact_sheet.company}'s filing: {source.excerpt}"] + computed)
    claim.label = LABELS[nli(premise, claim.text)]
    # The model is weak with numbers ("Leverage is 5.8x" passed against a sentence with no
    # 5.8 in it), so a claim can only be verified if its numbers are in the cited source
    # or a metric computed from it.
    if claim.label == "verified" and not numbers(claim.text) <= numbers(_number_text(fact_sheet, {source.id})):
        claim.label = "unsupported"
    return claim


def check_claims(claims: list[Claim], fact_sheet: FactSheet) -> list[Claim]:
    """Every claim comes back verified, contested or unsupported, or this raises."""
    return [check_claim(c, fact_sheet) for c in claims]

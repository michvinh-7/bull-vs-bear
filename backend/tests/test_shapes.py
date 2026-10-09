"""Guards the hour-0 contract: shared examples must parse into the backend models."""
import json
from pathlib import Path

from app import metrics
from app.schemas import CommitteeBrief, FactSheet, LineMessage

EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"


def test_examples_match_models():
    FactSheet.model_validate(json.loads((EXAMPLES / "fact_sheet.json").read_text()))
    for line in json.loads((EXAMPLES / "line_messages.json").read_text()):
        LineMessage.model_validate(line)
    CommitteeBrief.model_validate(json.loads((EXAMPLES / "committee_brief.json").read_text()))


def test_metrics_basic():
    assert metrics.leverage(580, 100) == 5.8
    assert metrics.interest_coverage(190, 100) == 1.9
    assert metrics.floating_rate_pct(62, 100) == 62.0
    assert metrics.liquidity(110, 300) == 410
    assert metrics.next_big_maturity({2026: 5, 2027: 5, 2028: 90}) == 2028

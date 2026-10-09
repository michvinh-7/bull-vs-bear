"""Guards the hour-0 contract: shared examples parse, ids cross-reference, and
shared/schemas/*.json are in sync with app/schemas.py."""
import json
from pathlib import Path

from app import metrics
from app.schemas import CommitteeBrief, FactSheet, LineMessage, Positions
from scripts.export_schemas import OUT, SHAPES, render

EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_examples_match_models():
    FactSheet.model_validate(load("fact_sheet.json"))
    Positions.model_validate(load("positions.json"))
    for line in load("line_messages.json"):
        LineMessage.model_validate(line)
    CommitteeBrief.model_validate(load("committee_brief.json"))


def test_example_ids_resolve():
    sheet = FactSheet.model_validate(load("fact_sheet.json"))
    source_ids = {s.id for s in sheet.sources}
    lines = [LineMessage.model_validate(x) for x in load("line_messages.json")]
    claim_ids = {c.id for line in lines for c in line.claims}
    positions = Positions.model_validate(load("positions.json"))
    brief = CommitteeBrief.model_validate(load("committee_brief.json"))

    assert len(source_ids) == len(sheet.sources), "duplicate source ids"
    for m in sheet.metrics:
        assert set(m.source_ids) <= source_ids, m.name
    for d in sheet.debt:
        assert d.source_id in source_ids, d.name
    for side in (positions.bull, positions.bear):
        assert {p.source_id for p in side.points} - {None} <= source_ids
    for line in lines:
        for c in line.claims:
            assert c.source_id is None or c.source_id in source_ids, c.id
            assert c.id.startswith(f"t{line.turn}c"), c.id
    for item in [*brief.agreed, *brief.disputed]:
        assert set(item.claim_ids) <= claim_ids
    assert {u.claim_id for u in brief.unsupported} <= claim_ids


def test_json_schemas_in_sync():
    for name, model in SHAPES.items():
        on_disk = (OUT / f"{name}.schema.json").read_text(encoding="utf-8")
        assert on_disk == render(model), f"Run `python -m scripts.export_schemas` ({name} is stale)"


def test_metrics_basic():
    assert metrics.leverage(580, 100) == 5.8
    assert metrics.interest_coverage(190, 100) == 1.9
    assert metrics.floating_rate_pct(62, 100) == 62.0
    assert metrics.liquidity(110, 300) == 410
    assert metrics.next_big_maturity({2026: 5, 2027: 5, 2028: 90}) == 2028

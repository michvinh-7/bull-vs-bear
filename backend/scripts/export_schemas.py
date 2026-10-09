"""Writes shared/schemas/*.schema.json from backend/app/schemas.py.

Run from backend/:  python -m scripts.export_schemas
"""
import json
from pathlib import Path

from app.schemas import CommitteeBrief, FactSheet, LineMessage, Positions

OUT = Path(__file__).resolve().parents[2] / "shared" / "schemas"

SHAPES = {
    "fact_sheet": FactSheet,
    "positions": Positions,
    "line_message": LineMessage,
    "committee_brief": CommitteeBrief,
}


def render(model) -> str:
    return json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    for name, model in SHAPES.items():
        (OUT / f"{name}.schema.json").write_text(render(model), encoding="utf-8")
        print(f"wrote shared/schemas/{name}.schema.json")

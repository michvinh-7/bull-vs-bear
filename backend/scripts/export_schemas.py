"""Writes shared/schemas/*.schema.json from backend/app/schemas.py, and copies
shared/examples/*.json into backend/app/examples/ (Railway only ships backend/).

Run from backend/:  python -m scripts.export_schemas
"""
import json
import shutil
from pathlib import Path

from app.schemas import CommitteeBrief, FactSheet, LineMessage, Positions

OUT = Path(__file__).resolve().parents[2] / "shared" / "schemas"
SHARED_EXAMPLES = Path(__file__).resolve().parents[2] / "shared" / "examples"
BACKEND_EXAMPLES = Path(__file__).resolve().parents[1] / "app" / "examples"

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
    for src in SHARED_EXAMPLES.glob("*.json"):
        shutil.copyfile(src, BACKEND_EXAMPLES / src.name)
        print(f"copied shared/examples/{src.name} -> backend/app/examples/")

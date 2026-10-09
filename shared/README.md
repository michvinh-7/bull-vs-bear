# Shared data shapes

Agreed in hour 0. **Any change gets announced to the whole team** and made in all three places:

| Shape | JSON Schema | Backend | Frontend |
|---|---|---|---|
| Fact sheet | `schemas/fact_sheet.schema.json` | `backend/app/schemas.py` | `frontend/lib/types.ts` |
| Line message | `schemas/line_message.schema.json` | same | same |
| Committee brief | `schemas/committee_brief.schema.json` | same | same |

`examples/` holds fake data. The frontend builds against copies in `frontend/lib/mock/`
(refresh with `npm run sync-shapes`), and `backend/tests/test_shapes.py` fails if the
examples stop matching the backend models.

# Let Agents Cook — Claude Design import

Drop **all exported files** from Claude Design here. The Cursor agent maps them into `frontend/components/marketing/` and related routes.

## What to upload

Copy everything from your Claude Design export into this folder (keep subfolders if the export has them):

| Include | Examples |
|---------|----------|
| HTML / JSX / TSX | `index.html`, page components |
| CSS | `styles.css`, `globals.css` |
| JavaScript | bundled or per-page `.js` |
| Assets | `images/`, `icons/`, `fonts/`, SVGs |
| Prototype | single-file prototype with routing, if provided |
| Screenshots | optional PNG references |

## Suggested layout (either is fine)

```
design/letagentscook-claude/
  README.md          ← this file
  index.html         ← or prototype entry
  catalog.html
  how-it-works.html
  verify-first.html
  styles/
  assets/
```

## After upload

Tell the agent in chat: **„súbory sú v design/letagentscook-claude“** — it will integrate into the Next.js app (no app/login links; Gumroad-only purchase CTAs).

## Target routes in code

| Design page | App route |
|-------------|-----------|
| Home | `/` (marketing host) |
| Catalog | `/skills` |
| Product detail | `/skills/[slug]` |
| How it works | `/how-it-works` |
| Verify-first | `/verify-first` |
| Free eval checklist | `/skills/eval` (Phase 2) |

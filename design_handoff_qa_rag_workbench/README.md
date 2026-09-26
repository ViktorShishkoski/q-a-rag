# Handoff: Q&A RAG — light workbench UI

## Overview
Redesign of the single-screen Q&A RAG app (upload documents → ask a question → get an
answer with cited retrieved chunks). The new layout replaces the stacked single-column
form with a three-zone workbench: a persistent corpus rail, a composer with retrieval
controls, and an answer + retrieved-chunks pairing.

## About the Design Files
The files in this bundle are **design references created in HTML** — a prototype showing
intended look and behavior, not production code to copy verbatim. The task is to
**recreate the design in the target codebase** (React + Vite + Tailwind) using its
existing patterns, components and conventions. `QARag.reference.jsx` is a direct
Tailwind translation provided as a starting point, not a drop-in: split it into the
codebase's component structure and wire it to the real API.

## Fidelity
**High-fidelity.** Colors, typography, spacing, radii and interaction states are final.
Recreate pixel-accurately, substituting equivalent primitives where the codebase already
has them (button, card, badge, tooltip).

## Screens / Views

### 1. Console (single screen, all states)
**Purpose:** the user uploads documents, asks a question, reads the answer, and checks
which chunks it came from.

**Layout**
- Root: `min-h-screen` column, page background `#f6f5f3`, text `#1c1a17`.
- Header: sticky, `h-15` (60px), `px-7`, bottom border `1px #e6e3dd`,
  background `#9DE2DA`, `z-5`. Space-between: brand block left, meta + status right.
- Body: `grid grid-cols-[300px_minmax(0,1fr)] items-start`.
- Left rail (`aside`): sticky `top-15`, `min-h-[calc(100vh-60px)]`, background `#fffefc`,
  right border `1px #e6e3dd`, `px-5 py-[22px]`, column with `gap-[22px]`.
- Main: `px-[34px] pt-[30px] pb-15`, `max-w-[980px]`, background `#FFFFFF`,
  column with `gap-[22px]`.
- Answer row: `grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start`.

**Components**

*Brand block (header left)* — baseline-aligned flex, `gap-3`, `rounded-[5px]`,
background `linear-gradient(180deg,#69D9CF,#F4EAE0)`.
- "Q&A RAG": 16px / 700 / `-0.01em`, color `#116A72`.
- "retrieval console": mono 11px / `0.04em`, color `#316D6D`.

*Header meta* — mono 11px `#8c867d`, `gap-4`: "{docCount} docs", "{chunkCount} chunks".

*Status pill* — `rounded-full`, border `1px #d7e5e3`, background `#f0f7f6`,
padding `5px 11px 5px 9px`; 6px dot `oklch(0.6 0.13 165)` pulsing 2.4s ease-in-out
infinite (opacity 1 → 0.25); label mono 11px `oklch(0.42 0.07 175)`.

*Section label* (Corpus / Indexed / Answer / Retrieved) — mono 10px, uppercase,
`0.09em`, color `#a09a91`.

*Upload dropzone* — `label` wrapping a hidden file input; column, centered,
`gap-2`, `px-[14px] py-5`, `rounded-[10px]`, dashed `1px #cfcac1`,
background `#faf9f7`. 18px upload arrow icon, stroke `#8c867d`, width 1.6.
Copy: "Drop a **PDF** or **Markdown** file / or click to browse" — 12.5px `#6f6a62`,
`leading-[1.5]`; the two format words 600 weight `#3d3a35`.
Hover: border `oklch(0.6 0.09 205)`, background `#f4f8f9`; 150ms transition.

*Indexed document row* — `px-[11px] py-[10px] rounded-[9px]`, cursor pointer, 150ms
transition. Unselected: border `1px #efece7`, background `#fdfcfa`. Selected: border
`1px #cfe0e3`, background `#f4f9fa`. Hover (unselected): border `#d8d3ca`,
background `#fffefc`.
- 6×6 square dot, `rounded-[2px]`, `mt-[5px]`; `oklch(0.55 0.11 205)` when selected,
  else `#d3cec5`.
- Title: 12.5px / 500 / `leading-[1.4]` `#2a2723`, truncated.
- Meta row (`mt-[5px]`, `gap-2`, mono 10.5px `#a09a91`): kind chip
  (`px-[5px] py-px`, border `1px #e2ded7`, `rounded-[3px]`, uppercase `0.04em`)
  then "{chunks} chunks".

*Rail footer* — `mt-auto pt-4`, top border `1px #efece7`, mono 10.5px `#b3ada3`,
`leading-[1.7]`: "embed · bge-small-en", "gen · gpt-4o-mini".

*Composer card* — background `#fffefc`, border `1px #e6e3dd`, `rounded-xl`,
shadow `0 1px 2px rgba(28,26,23,0.03)`.
- Textarea: 3 rows, borderless, transparent, `resize-none`, no outline,
  `pt-[18px] px-5 pb-1`, 16px / `leading-[1.55]` `#1c1a17`, `-0.005em`.
  Placeholder "Ask a question about your documents…" in `#a8a29b`.
- Control bar: top border `1px #f0ede8`, `py-3 pl-5 pr-4`, space-between.

*Top-k stepper* — mono 11px label "top k" `#8c867d`; group with border `1px #e2ded7`,
`rounded-[7px]`, background `#faf9f7`, overflow hidden. − / + buttons 24×26,
transparent, `#6f6a62`, hover background `#efece7`. Value: mono 12px `#2a2723`,
`min-w-6` centered. Clamp 1–20.

*Rerank toggle* — `px-[9px] py-[5px] rounded-[7px] gap-[7px]`, mono 11px label.
On: border `#cfe0e3`, background `#f2f8f9`, text `oklch(0.5 0.11 205)`, 11px box
filled with the accent and `inset 0 0 0 2px #f2f8f9`. Off: border `#e2ded7`,
background `#faf9f7`, text `#6f6a62`, box border `#cfcac1` transparent fill.

*Scope button* — same metrics as rerank, always border `#e2ded7` / background
`#faf9f7` / text `#6f6a62`; hover border `#d3cec5`. Label toggles
"all documents" ⇄ "{kind} only".

*Ask button* — `px-4 py-[9px] rounded-lg`, no border, 13.5px / 600, white text,
background `oklch(0.5 0.11 205)`; shadow `0 1px 2px rgba(28,26,23,0.12)`.
Trailing "⏎" mono 10.5px at 60% opacity. Busy: label "Asking", background
`oklch(0.62 0.07 205)`, `cursor-wait`, leading 6px pulsing dot (1s).

*Suggestion chips* — shown when not busy. Row with `gap-2`, prefixed by mono 10.5px
uppercase "try" `#b3ada3`. Chip: `px-[11px] py-1.5 rounded-full`, border
`1px #e6e3dd`, background `#fffefc`, 12.5px `#5c574f`; hover border
`oklch(0.7 0.06 205)`, text `oklch(0.45 0.1 205)`. Clicking fills the composer.

*Loading card* — replaces the answer while busy. Card metrics as the composer,
`p-[22px]`. Stage line: mono 11px `oklch(0.5 0.1 205)`, `0.04em`, `mb-4`, cycling
"searching index…" → "reranking {topK*4} candidates…" → "drafting answer…" at 750ms.
Below: three 11px `rounded-[3px]` bars at 92% / 78% / 55% width, shimmer
`linear-gradient(90deg,#f1eee9,#e6e2db 50%,#f1eee9)` with `background-size:320px 100%`,
1.3s linear infinite, `background-position -320px → 320px`.

*Answer card* — card metrics as the composer, `px-[26px] py-6`.
Header row: "Answer" label left; mono 10.5px `#b3ada3` latency + token count right.
Body: 15.5px / `leading-[1.68]` `#26241f`, `text-wrap: pretty`.
Footer (`mt-[22px] pt-4`, top border `1px #f0ede8`): "Copy" and "Regenerate"
(`px-2.5 py-[5px] rounded-[7px]`, border `1px #e6e3dd`, background `#fffefc`,
12px `#6f6a62`, hover border `#d3cec5`); right-aligned 28×28 ↑ / ↓ feedback buttons,
same border treatment, text `#8c867d`.

*Inline citation* — `sup`, mono 9.5px, `min-w-[15px]`, `px-[3px] py-px`,
`rounded-[3px]`, `ml-0.5`, centered, cursor pointer. Idle: background `#eef4f5`,
text `oklch(0.5 0.11 205)`. Hovered: background accent, text white. Hovering a citation
also highlights its retrieved card, and vice versa — one shared `hovered` id.

*Retrieved chunk card* — `px-[13px] py-3 rounded-[10px]`, 120ms transition.
Idle: border `1px #e6e3dd`, background `#fffefc`, no shadow. Highlighted: border
`1px #bcd6da`, background `#f6fbfb`, shadow `0 1px 3px rgba(28,26,23,0.06)`.
- Number badge: `min-w-[18px] px-[5px] py-px rounded-[4px]`, mono 10.5px; idle
  background `#eef4f5` / accent text, highlighted accent background / white text.
- Location: mono 10.5px `#a09a91` ("p. 84 · c/311").
- Snippet: 12.5px / `leading-[1.55]` `#57524b`.
- Score row (`mt-[9px] gap-2`): 3px track `#efece7` `rounded-[2px]`, fill width
  `score*100%` in `#c9d9dc` (accent when highlighted); mono 10.5px score `#8c867d`,
  two decimals.

## Interactions & Behavior
- **Ask**: click the Ask button, or Enter in the textarea (Shift+Enter newlines).
  Empty/whitespace query is a no-op.
- **Busy sequence**: on ask, `busy=true`, `answered=false`, `stage=0`; a 750ms
  interval advances stage 0→1→2, then clears and sets `busy=false, answered=true`.
  In production, drive these three stages off real retrieval / rerank / stream events
  rather than a timer.
- **Citation ↔ chunk cross-highlight**: mouseenter/mouseleave on either the `sup` or the
  chunk card sets/clears a single `hovered` chunk number.
- **Document select**: clicking a rail row sets `selected`; the scope button's
  "{kind} only" label reads from it.
- **Suggestion chip**: sets the query text; does not auto-submit.
- **Transitions**: 150ms on dropzone and rail rows (border + background), 120ms on
  chunk cards and citations. Keyframes: `pulseDot` (opacity 1/0.25/1) and `shimmer`.
- **Responsive**: below ~1100px collapse to one column — rail becomes a collapsible
  drawer or a horizontal strip, and the answer/chunks grid stacks with chunks under the
  answer. Not designed in the prototype; follow the codebase's breakpoints.
- Clean up the interval on unmount.

## State Management
| state | type | notes |
|---|---|---|
| `query` | string | textarea value |
| `topK` | number | 1–20, default 5 |
| `rerank` | boolean | default true |
| `scopeAll` | boolean | default true |
| `selected` | number | index into documents |
| `busy` | boolean | request in flight |
| `stage` | 0 \| 1 \| 2 | retrieval progress label |
| `answered` | boolean | an answer is present |
| `hovered` | number \| null | cross-highlighted chunk |

Data needed: document list (`title`, `kind`, `chunks`), and per answer the body text
with citation markers, retrieved chunks (`n`, `loc`, `snippet`, `score`), latency and
token count, plus the embed and generation model names for the rail footer.

## Design Tokens
**Accent** `oklch(0.5 0.11 205)` · hover/active `oklch(0.55 0.11 205)` ·
busy `oklch(0.62 0.07 205)` · tint `#eef4f5` · surface tint `#f2f8f9` /
`#f4f9fa` / `#f6fbfb` · accent border `#cfe0e3` / `#bcd6da` / `#d7e5e3` ·
muted accent `#c9d9dc`
**Header** `#9DE2DA`; brand gradient `#69D9CF → #F4EAE0`; brand text `#116A72`,
sub `#316D6D`
**Neutrals** page `#f6f5f3` · surface `#fffefc` · surface-2 `#faf9f7` /
`#fdfcfa` · main `#FFFFFF` · borders `#e6e3dd` `#e2ded7` `#efece7`
`#f0ede8` `#cfcac1` `#d3cec5` `#d8d3ca` · shimmer `#f1eee9`/`#e6e2db`
**Text** `#1c1a17` `#26241f` `#2a2723` `#3d3a35` `#57524b` `#5c574f`
`#6f6a62` `#8c867d` `#a09a91` `#b3ada3` `#c2bcb2`; placeholder `#a8a29b`
**Success dot** `oklch(0.6 0.13 165)`; success text `oklch(0.42 0.07 175)`
**Type** Libre Franklin 400/500/600/700; IBM Plex Mono 400/500.
Scale: 16 / 15.5 / 13.5 / 12.5 / 12 / 11 / 10.5 / 10px.
**Radius** 3 · 4 · 5 · 7 · 9 · 10 · 12 · 999px
**Shadow** `0 1px 2px rgba(28,26,23,0.03)` (cards) ·
`0 1px 2px rgba(28,26,23,0.12)` (Ask) · `0 1px 3px rgba(28,26,23,0.06)` (hover)
**Spacing** 4 · 5 · 7 · 8 · 9 · 10 · 11 · 12 · 14 · 16 · 18 · 20 · 22 · 24 · 26 ·
28 · 30 · 34 · 60px

## Assets
None. The one icon (upload arrow) is inline SVG, included in the reference component.
Fonts load from Google Fonts — `Libre+Franklin:wght@400;500;600;700` and
`IBM+Plex+Mono:wght@400;500`; self-host them if the codebase already self-hosts fonts.

## Files
- `Option A - Light workbench.dc.html` — the design prototype (open in a browser)
- `QARag.reference.jsx` — Tailwind + React translation, starting point
- `tailwind.tokens.md` — the tokens above as a Tailwind theme extension

# The summary diagram

One figure per project, computed entirely in SPARQL and rendered inline by an SVG view. The query
returns ready-to-embed markup in an `svg` column; the view declares `gen:SvgView` alongside
`gen:ResourceView`.

```
 ┌──────────────────────────────────────────────────────────┐
 │ 💡 Knowledge                                             │   general statements
 └──────────────────────────────────────────────────────────┘
                             ▲
 ┌──────────────────────────────────────────────────────────┐
 │ ⚖ Evidence & Arguments                                   │   results, analyses, proofs
 └──────────────────────────────────────────────────────────┘
              ▲                            ▲
 ┌───────────────────────┐  ➤  ┌───────────────────────────┐
 │ 🔬 Activities         │     │ 📦 Outputs                │
 └───────────────────────┘     └───────────────────────────┘
              ▲                            ▲
 ┌──────────────────────────────────────────────────────────┐
 │ 👥 People                                                │
 └──────────────────────────────────────────────────────────┘
 ┌──────────────────────────────────────────────────────────┐
 │ 🏛 Institutions                                           │
 └──────────────────────────────────────────────────────────┘
```

Each entry is `<icon> <label> · <type/role>`, left-aligned, and links to the entity's part page.

## Design rules

These are the rules that survived iteration; each replaced something that looked fine in isolation and
read badly on the page.

**Frame the topic, not the entry.** One bordered light-grey panel per layer, entries as plain text
inside it. Boxing every entry produced 33 frames on a real project and read as noise.

**Left-align everything**, including the panel headings, indented to the same left edge as the entries.

**Put the type immediately after the label, in the same `<text>` element**, as a sibling `tspan` after
the link, with `dx` for the gap:

```
<text><a><title>full label</title><tspan>🧬 short label</tspan></a><tspan dx="9" font-size="9">type</tspan></text>
```

Text-flow layout then places the type exactly where the label ends, with no width estimation. Keeping
the `<a>` *inside* the `<text>` is what makes the label the only part that takes the page's link colour;
the type stays normal text. Sentence-case headings; drop the letter-spacing that all-caps needed.

**One line per entry**, truncated with an ellipsis, with the full text in a `<title>` so hovering shows
everything. Two-line wrapping works (break at the last space within the cap using
`replace(?t, "^(.{1,N})[ ].*$", "$1")`) but costs a third of the vertical space for the few entries that
need it.

**Arrowheads, not arrows.** A single glyph (`➤`, U+27A4) at the centre of the gap between panels, with
the upward ones rotated `rotate(-90 x y)`. Full lines with heads added visual weight without adding
information.

## Sizing: derive it, never guess

Two numbers drive everything:

```python
PANEL_W, SCALE = 1395, 1.6      # target render width, and units-to-pixels
CANVAS = int(PANEL_W / SCALE)   # the viewBox width
```

The declared `width` equals the panel width, so the figure fills the column at 1:1 and 10 natural units
of text render at 16 px — matching 12 pt body text. Declaring a *larger* width also works (CSS
`max-width:100%` scales it down to the panel) but then the text ends up smaller than the page's.

Every column width derives from the canvas:

```python
CONTENT = CANVAS - 2 * MARGIN          # widest panel, outer
FULLCOL = CONTENT - 2 * PADX           # single-column content width
col(n)  = (FULLCOL - (n-1) * COLGAP) // n
```

so widening the canvas automatically pushes truncation and wrapping later. **Never hardcode a column
x-position or width**: an earlier version did, and the right-hand panel ran off the canvas the moment a
column widened.

Truncation follows from the width too, per row, reserving space for that row's type text:

```sparql
bind(xsd:integer(floor((COLW - 26 - strlen(?typ) * 4.6) / 5.15)) as ?cap)
```

The constants are measured average advance widths (5.15 px per character at 10 px, 4.6 at 9 px), not
guesses. This formula is also the label budget authors should write to; see
[naming.md](naming.md). If a row can carry its type on the same line, the label cap must reserve room for it — getting
that wrong overflows exactly the rows whose text happens to fit.

For the arrow glyph, measure the font rather than eyeballing:

```python
from PIL import ImageFont
f = ImageFont.truetype('…/DejaVuSans.ttf', 100)
f.getmetrics(), f.getbbox('➤')     # → ink 0.84em long, 0.65em thick, centred 0.315em above baseline
```

At `font-size` 30 that is 25.2 units of ink in a 28-unit gap — deliberately close-fitting, because a
smaller arrow reads as a stray character rather than a connector. The 0.315em figure also sets the placement
nudge: `rotate(-90 x y)` keeps vertical centring exact (rotation preserves the baseline midpoint) but
maps the glyph's ascent onto the horizontal axis, so it lands left of the anchor — compensate with
`x + round(0.315 * font_size)`.

## Monochrome emoji

Emoji render in colour when the browser falls back to a system colour-emoji font. If the host page
bundles a monochrome emoji webfont, **use the page's own font stack on the root `<svg>`**:

```
font-family="Noto Emoji, Inter, Verdana, Helvetica, sans-serif"
```

The webfont's `unicode-range` covers only emoji code points, so Latin text still falls through to the
text font. A bare `font-family="sans-serif"` bypasses the stack and every emoji comes back in colour.
Write multi-word family names **unquoted** — CSS allows it — so no backslashes end up in the escaped
SPARQL. Note that a glyph *outside* the webfont's range (`➤` is) simply resolves to the text font, which
is equally monochrome.

## Query structure

One aggregate subquery per layer, each returning that layer's rendered fragment and its item count; the
outer `SELECT` does all layout arithmetic from those counts and places each layer with
`<g transform="translate(x,y)">`. No layer needs to know another's size, and the whole figure is one
row.

Within a layer, per-entry vertical index comes from the ranking pattern in
[sparql-cookbook.md](sparql-cookbook.md) (trap 7). Two structural constraints from that page apply here
and are easy to violate:

- the ranking copy of the item pattern must be a **flat** pattern inside the `OPTIONAL`, not a
  sub-`SELECT`;
- if a layer is a `UNION` of two sources, its membership `SERVICE` must go **inside each arm**.

An optional **title header** sits above the topmost layer: a further `OPTIONAL` picks the newest
member-signed Space definition for the project and binds its label and date range, which the outer
`SELECT` renders as two centred lines. The zones start at `?hd` rather than a constant, and `?hd` falls
back to the same top offset the headerless layout would use — so a deployment whose projects are not
Spaces, or whose Space carries no label, gets the old geometry exactly and pays nothing for the block.
Keep its member-pubkey `SERVICE` under a distinct variable name (`?memberPubkeysHd`): the per-layer
subqueries each bind `?memberPubkeys` in their own scope, and reusing the name across the outer scope
silently constrains them all.

## Authoring rules for the markup

- Write **explicit end tags** (`<rect …></rect>`); inline SVG is parsed under HTML rules, where a
  self-closing slash is ignored and following siblings get swallowed.
- Use **camelCase** attribute spellings (`viewBox`, `preserveAspectRatio`).
- XML-escape all data-derived text: `replace(replace(replace(?t, "&", "&amp;"), "<", "&lt;"), ">", "&gt;")`.
  A literal `&` in a heading must be written `&amp;` too.
- Emit **root-relative** links (`/part?id=<encode_for_uri(iri)>`); the rendering component appends the
  page context.
- Keep `fill` attributes on links as a fallback for standalone rendering, even though page CSS overrides
  them.

## Verifying the output

Never eyeball the figure alone. Parse it and assert the geometry — this is what caught every layout bug:

```python
root = ET.fromstring(svg)                     # well-formedness
# resolve <g transform="translate(x,y)"> offsets, then for every text run:
#   estimate width = len(text) * font_size * 0.55  (+ the type run, + the icon)
#   assert it fits inside the panel rect it sits in
#   assert no two panels overlap
#   assert nothing exceeds the viewBox
```

For wrapped text, additionally assert that the lines **reconstruct the original**: `l1 + " " + l2` must
equal the `<title>`. A regex-based line break is exactly the kind of thing that silently drops a word.

To preview outside the app, wrap the SVG in a page that reproduces the host's conditions: the emoji
`@font-face` rule, a panel div of the target width with `max-width:100%; height:auto`, the link colour
rule, and a line of body text at the real size for comparison.

## Generator

[../generator/project_summary_svg.py](../generator/project_summary_svg.py) implements all of the above.
Its configuration block is the only part a deployment edits: the layer definitions (assertion pattern,
type expression, icon expression, column count) and the two sizing numbers. Everything else — widths,
caps, panel heights, arrow placement, the ranking joins — derives from those.

Treat the generator as the source of truth and regenerate; never hand-edit the emitted SPARQL, which is
several hundred lines of concatenated string literals.

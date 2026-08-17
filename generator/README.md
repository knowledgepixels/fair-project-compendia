# Generator

`project_summary_svg.py` emits the SPARQL query behind the summary diagram. It takes no arguments and
writes the query to stdout:

```bash
python3 project_summary_svg.py > query.rq
```

## Configuring

Edit the `CONFIG` block near the top:

- `PANEL_W`, `SCALE` — target render width in pixels, and the natural-units-to-pixels factor. Pick
  `SCALE` so that `10 * SCALE` equals the host page's body text size in pixels.
- `ZCFG` — one entry per layer: `(column width, type expression, icon expression, columns, panel icon)`.
- `PAT` — the assertion pattern that finds a layer's items, with `ITEM` as a placeholder for the item
  variable.
- `RANKS` — optional per-layer sort-key expressions (role orderings).
- `PITCH`, `COLGAP`, `PADX`, `ARROWGAP`, `ARROW_SIZE` — spacing.

Layer widths, truncation caps, panel heights, arrow positions and the whole ranking apparatus derive
from those. Do not hardcode positions; see ../docs/svg-diagram.md for why.

## Testing before publishing

```bash
python3 project_summary_svg.py > q.rq
# substitute the project parameter and run it (POST, not GET)
sed 's|values ?_project_multi_iri {}|values ?_project_multi_iri { <PROJECT-IRI> }|g' q.rq > q-test.rq
curl -s -X POST "<endpoint>/repo/full" --data-urlencode "query@q-test.rq" \
     -H "Accept: application/sparql-results+json" > out.json
```

Then extract the `svg` value and check it: parse it as XML, resolve the `<g transform>` offsets, and
assert that every text run fits its panel, that panels do not overlap, and that nothing exceeds the
viewBox. The verification recipe is in ../docs/svg-diagram.md.

## Adding a layer

1. add its pattern to `PAT` and its entry to `ZCFG`;
2. add a height expression and a Y offset alongside the others in the layout section;
3. add its `zone(...)` call to the `QUERY` template and its `zone_svg(...)` call to `SVG`;
4. if it needs a role ordering, add an expression to `RANKS`.

A layer whose items come from two different sources is a `UNION` — see the two structural constraints in
../docs/sparql-cookbook.md (traps 2 and 3) before writing it.

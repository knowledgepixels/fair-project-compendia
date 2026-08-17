# FAIR Project Compendia

A reusable pattern for describing a **research project as nanopublications** — its activities, the
evidence they produced, the knowledge that evidence supports, its outputs, its people and their
institutions — and for rendering that description as a **one-page diagram** plus **per-entity detail
pages** in [Nanodash](https://github.com/knowledgepixels/nanodash).

Nothing here is specific to a funder, a programme or a discipline. Every vocabulary term, predicate
and layout constant is stated explicitly so that a new deployment can adopt, replace or extend it.

## The idea in one page

A project compendium is six **layers**, each a set of resources with a shared type, connected by a
small number of relations:

```
                    Knowledge          general statements the project contributed to
                        ▲
            Evidence & Arguments       empirical results and reasoning that support them
                        ▲
        Activities  ──▶  Outputs       what was done, and what it produced
                        ▲
                     People            who did it
                        ▲
                  Institutions         where they did it, and who paid
```

Read upward, it is an argument: institutions host people, people run activities, activities yield
outputs and evidence, evidence supports knowledge claims. Read downward, it is provenance: every
claim can be traced to the result, the activity and the person behind it.

Each layer is *queryable*, so the same data drives:

- a **summary diagram** (one SVG figure per project, [docs/svg-diagram.md](docs/svg-diagram.md)),
- **list views** per layer on the project page,
- **detail pages** for individual entities, with property/value tables and actions
  ([docs/views-and-actions.md](docs/views-and-actions.md)).

## Why nanopublications

Three properties of the substrate shape the whole design:

1. **Each statement carries its own provenance and attribution.** A claim transcribed from a paper
   can be attributed to that paper's authors while the nanopub is created by whoever curates the
   compendium — a distinction that matters as soon as anyone asks "who says so?".
2. **Statements are versioned, not edited.** Corrections are new nanopubs that supersede old ones.
   This forces an explicit decision about entity identity, covered in
   [docs/publishing.md](docs/publishing.md).
3. **Anyone can add a layer without permission.** A second party can publish evidence that supports —
   or contradicts — someone else's claim. The compendium is therefore always a *view over the
   network*, restricted to the publishers a project trusts, never a closed database.

## Repository map

| Path | Contents |
|---|---|
| [docs/model.md](docs/model.md) | The layers, their entity types and the relations between them |
| [docs/vocabularies.md](docs/vocabularies.md) | Which terms to use, which to avoid, and why — including the naming of the evidence layer |
| [docs/templates.md](docs/templates.md) | The assertion templates a deployment needs, with their statement shapes |
| [docs/views-and-actions.md](docs/views-and-actions.md) | Project-level and part-level views, property/value tables, entry vs. result actions |
| [docs/svg-diagram.md](docs/svg-diagram.md) | The summary figure: design rules, layout algorithm, sizing, icons |
| [docs/sparql-cookbook.md](docs/sparql-cookbook.md) | Patterns and traps when querying nanopublications with RDF4J behind grlc |
| [docs/publishing.md](docs/publishing.md) | Identity, versioning, timestamps, string escaping, verification |
| [generator/project_summary_svg.py](generator/project_summary_svg.py) | Configurable generator that emits the diagram query |
| [generator/README.md](generator/README.md) | How to configure, test and extend the generator |

## Adopting this in a new deployment

1. Decide the **layers you actually have data for**. The model degrades gracefully: a project with
   no evidence layer simply renders a compendium without that band.
2. Fix the **predicate set** per layer ([docs/model.md](docs/model.md)). Most deployments reuse an
   existing project vocabulary rather than minting one.
3. Publish the **templates** so that contributors can add entries through forms rather than by hand
   ([docs/templates.md](docs/templates.md)).
4. Publish the **queries and views**, and activate them on each project space
   ([docs/views-and-actions.md](docs/views-and-actions.md)).
5. Configure and run the **diagram generator**, then publish its output as an SVG view
   ([docs/svg-diagram.md](docs/svg-diagram.md)).

Read [docs/sparql-cookbook.md](docs/sparql-cookbook.md) before writing the first query. It documents
failure modes that produce *wrong results rather than errors*, which cost far more to find later.

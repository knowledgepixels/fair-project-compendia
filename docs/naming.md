# Naming entries

Every entry in a compendium is seen almost exclusively as **one short label on one line** — in the
summary diagram, in the per-layer list views, in link text and in breadcrumbs. The description is one
click away and mostly unread. So the label is not a caption for the entity; for most readers it *is*
the entity.

Two rules apply everywhere, before the per-layer conventions:

**A label must say what the thing is without help.** It is tempting to drop the kind word because the
type already renders beside it (`· observational study`, `· computational evidence`) — an entry
reading "Roadside pollution in five cities · observational study" wastes no width. Resist it. The
type label is a property of *this rendering*; the label travels — into search results, hover titles,
other projects' pages, citations — where nothing accompanies it. A name that only makes sense next to
its type is a name that breaks the moment it leaves the diagram.

**Don't title it like a paper.** Activities and evidence items are not publications, and an
article-style title ("Mode and dynamics of traffic-related nitrogen dioxide accumulation in urban
street canyons", 94 characters) is both too long for the line and the wrong register. Name the work, then
put the paper's framing in `dct:description`, which the detail view shows in full.

## The character budget is computable

Do not guess a length. The diagram truncates a label to fit its column *minus that row's type text*,
so the budget follows from the layout:

```python
cap = int((column_width - icon_allowance - len(type_label) * TYPE_CW) / LABEL_CW)
```

Compute it once per layer from the generator's own configuration rather than eyeballing the rendered
figure — a longer type label buys a shorter name, which is why two entries in the same column can have
different budgets. In a typical single-column-width deployment this lands around 50 characters for a
two-column layer and around 140 for the full-width knowledge band.

Aim comfortably under the cap. A label at exactly the limit is one ontology-label revision away from
being truncated, and truncation is silent.

## Activities

Name the piece of work, and include the word that says what kind of work it was:

- *Roadside pollution study in five cities*
- *SensorCal development and validation study*
- *National air-quality monitoring programme*

Pattern: `<subject or object of study> <kind> [in <setting>]`. Scope words earn their place when they
distinguish this activity from a sibling ("in five cities" separates the field study from the method
work); drop them when they do not.

Where the OBI subtype is not literally a study — a surveillance process, a data-collection effort —
"study" can overclaim, which is why the third example above says "programme". "effort" and
"surveillance" work too, and the type label still carries the precise classification.

## Evidence & Arguments

This is the layer where naming goes wrong most often, in two opposite directions.

**Not the procedure.** "Sensor calibration", "cluster assignment", "pairwise classification" name
*things done* — which is what the Activities layer is for. An evidence item is the result that bears
on a claim, so name the result.

**Not the claim.** "Traffic dominates roadside pollution" is a knowledge statement, and the Knowledge
layer already carries it. Evidence records what was found, without asserting its generality.

The way through is a head noun that is itself evidential, chosen to match the item's ECO type:

| Head noun | Use for | Example |
|---|---|---|
| **results** | the output of a defined analysis | *Classification results for 309 site pairs* |
| **predictions** | a computed estimate | *Source prediction results from the dispersion model* |
| **observation** | a pattern seen in the data | *Observation of traffic-dominated episodes* |
| **corroboration** | agreement with an external source | *Corroboration by published measurements* |
| **benchmark** | a comparison against alternatives | *Benchmark against earlier models* |

Keep the set small and use it consistently: the head noun then carries the evidential reading, the
qualifier carries the content, and neither repeats the type label rendered beside it. A name built
this way reads as evidence without containing the word "evidence" — which matters, because
`... evidence · computational evidence` says it twice on one line.

## Knowledge

Statement wording is governed by AIDA (Atomic, Independent, Declarative, Absolute) and by the fact
that **the IRI is the text**. See the renaming cost below before publishing.

The layer holds two rungs, and each is written differently:

- **Specific findings** quantify and situate: *"Road traffic accounted for about 32% of measured
  nitrogen dioxide at five urban sites between 2012 and 2015."* Precision is the point;
  length is acceptable because these mostly appear behind their general statement.
- **General statements** are the reusable claims other projects can also speak to. These appear in the
  diagram, so they must fit one line, and they should be phrased so that a *different* project could
  plausibly link its own finding to the same sentence. That is the whole payoff: a statement narrow
  enough that only one project can ever reach it will never accumulate evidence.

Shorten by deleting words that carry no information at this rung — "individual urban monitoring sites
affected by road traffic" → "some urban sites"; "the dominant source of a pollutant can be determined
from high-resolution measurement data" → "high-resolution measurement can identify a pollutant's
dominant source". Most general statements shrink by a third with no loss.

Two limits on how far to generalise:

- **Keep the qualifier that makes a conditional claim true.** "In low-emission settings, background
  sources dominate" is a finding; the same sentence without the qualifier is false.
- **Stop before the truism.** Generalise far enough and every statement becomes textbook knowledge
  that no longer says what the project contributed. Keep at least one rung domain-anchored; a
  knowledge band of six fully generic lines reads thin.

## The cost of renaming, per layer

| Layer | Identity | Renaming costs |
|---|---|---|
| Activities, Evidence, Outputs | IRI is independent of the label | One superseding nanopub each. Reuse the introduced IRI (see [publishing.md](publishing.md)) and every inbound link survives. |
| Knowledge | **IRI encodes the sentence** | A new IRI. Every nanopub referencing the old sentence must be superseded — in practice all of its relation nanopubs, since general statements are usually not introduced anywhere themselves. |

So: renaming an activity or an evidence item is cheap and can be done whenever the name proves
unclear. Rewording a statement is not, and is worth getting right before the first publish.

When you do rewrite AIDA sentences, two mechanical details bite:

- **Encoding.** Spaces become `+`; `%` becomes `%25`; commas and full stops stay literal. Generate the
  IRI with the same function every time, and round-trip an existing IRI through it as a test before
  minting new ones.
- **Label patterns.** A relation nanopub's own label embeds truncated copies of both sentences. If you
  hand-author the superseding version, reproduce the truncation exactly (in Nanodash: 51 characters,
  then a trailing space stripped, then an ellipsis) or the labels drift apart across versions.

## Consistency across nanopubs

If two nanopubs give the same IRI different labels, view output becomes nondeterministic — queries
pick one with `sample()` or `min()`. When a second nanopub must repeat a label, repeat it identically;
when it does not need to, omit it and let the original stand. This is the same warning as in
[publishing.md](publishing.md), and renaming is exactly when it gets violated.

# The model

A compendium describes one **project**. In a Nanodash deployment the project is normally a *space*,
which gives it a page, a membership model and an authority boundary; nothing below depends on that
choice, only on the project having a stable IRI.

## Layers

| Layer | Entities are… | Typed as | Attached to the project by |
|---|---|---|---|
| Knowledge | general statements the project contributed to | `hycl:AIDA-Sentence` (or `hycl:Formula`) | indirectly, through the evidence/activities they cite |
| Evidence & Arguments | empirical results, analyses, interpretations, proofs | `eco:evidence` (+ a subclass) | `prov:wasGeneratedBy` an activity |
| Activities | studies, surveys, experiments, campaigns | `obi:investigation` (+ a subclass) | `dct:isPartOf` the project |
| Outputs | articles, datasets, software, presentations, blog posts | the predicate carries the kind | `<project> <kind-predicate> <output>` |
| People | individuals, by role | ORCID IRIs | one predicate per role |
| Institutions | organisations, by role | ROR IRIs | one predicate per role |

Inputs (data the project *reused* rather than produced) are a legitimate seventh layer; a deployment
that has them can render them to the left of the activities. Note that a resource can legitimately
appear as **both** an input and an output when a project reuses and extends the same collection.

## Relations

The whole model rests on six relations. Everything else is presentation.

```turtle
<activity>  dct:isPartOf            <project> .
<evidence>  prov:wasGeneratedBy     <activity> .
<evidence>  cito:isDocumentedBy     <output> .
<statement> cito:obtainsSupportFrom <evidence> .      # and/or the activity directly
<statement> hycl:hasMoreGeneralMeaningThan <statement> .
<project>   <role-or-kind>          <person|institution|output> .
```

Two design notes that are easy to get wrong:

**Support points from the claim to its grounds**, not the other way round. This direction was chosen
because a statement's template already offers a repeatable "obtains support from" field, so evidence
can be attached to existing claims without republishing any template — and because a claim naturally
cites its grounds, while grounds do not know which future claims will rest on them. The cost is that
"what does this evidence support?" is a reverse traversal; in SPARQL that is free, but it means an
evidence item's own nanopub is silent about its consumers.

**Activities sit between the project and the evidence.** It is tempting to attach evidence straight
to the project, but then the compendium cannot say *which* study produced a result, and the diagram
loses its middle band. Keeping the hop also gives a cheap way to find a project from an evidence item
(`evidence → activity → project`), which several queries rely on.

## Layer detail

### Activities

An activity is a planned process undertaken to produce knowledge. Use `obi:investigation` as the base
type and add a more specific subclass where one fits (observational, surveillance, clinical trial,
hypothesis-driven, and so on — see [vocabularies.md](vocabularies.md)). Recommended properties:

```turtle
<activity> a obi:investigation, <specific-subclass> ;
    rdfs:label "…" ;
    dct:description "…" ;
    dct:isPartOf <project> ;
    prov:wasAssociatedWith <orcid> ;          # repeatable: who conducted it
    rdfs:seeAlso <url> .                      # repeatable: registration, page, DOI
```

Display tip: ontology labels for subclasses read awkwardly in a UI ("observational investigation").
Rewriting `investigation` to `study` at display time gives "observational study" without touching the
data. For the label itself, see [naming.md](naming.md).

### Evidence & Arguments

An evidence item is an information artefact: a measurement, a classification, a statistical result, a
computed comparison, or an interpretation of those. It is **not** the dataset and **not** the paper —
those are inputs and outputs respectively.

```turtle
<evidence> a eco:evidence, <specific-subclass> ;
    rdfs:label "…" ;                          # keep short: it is a diagram entry
    dct:description "…" ;                     # the detail goes here
    prov:wasGeneratedBy <activity> ;          # repeatable
    cito:isDocumentedBy <output> .            # repeatable: where it is reported
```

Classify items rather than typing everything the same way. A compendium in which every item is
"computational evidence" tells the reader nothing; distinguishing combinatorial, similarity,
inferential, high-throughput and documented-statement evidence makes the layer informative and gives
the diagram meaningful per-type icons.

Keep labels short and put detail in `dct:description`. The label is what appears in the diagram, in
breadcrumbs and in link text; a sentence-long label is unusable in all three. Naming an evidence item
is easy to get wrong in two opposite directions — naming the procedure, or restating the claim — so
[naming.md](naming.md) gives a head-noun convention for it.

### Knowledge

Statements are English sentences that are Atomic, Independent, Declarative and Absolute (AIDA), whose
IRI *is* the sentence — the text is percent-encoded into the IRI, so a statement is self-describing
even with no nanopub introducing it. Two consequences:

- A relation nanopub alone (`A hasMoreGeneralMeaningThan B`) suffices to bring statements into the
  graph. It is cheap, and it does **not** claim the statements are true — only that they stand in a
  generality relation.
- Because the IRI is derived from the text, **the wording is frozen** once published. Rewording mints
  a different IRI and orphans every link, so every relation nanopub referencing it must be superseded.
  Decide the phrasing before publishing — [naming.md](naming.md) covers how general to go, and how far
  is too far.

Distinguish a project's own specific findings from the general statements they bear on. Specific
findings quantify ("about 32% of linked cases were clonal in country X between 2012 and 2015");
general statements are the reusable claims other projects can also speak to. Linking the two with
`hycl:hasMoreGeneralMeaningThan` is what lets a compendium express **what the project contributed to
the field** rather than merely what it measured.

That contribution can be qualified from the graph itself. If no other project's finding generalises to
a statement, this project provided its *first evidence*; if others do, it *increased* the evidence. A
statement that a proof establishes is *proved* instead: deduction does not accumulate, so the evidence
scale does not apply to it ([vocabularies.md](vocabularies.md) has the reasoning). A statement the
project only declares `gen:isRelevantFor` itself, with nothing generalising to it, is merely
*relevant* — the project vouches for it without having contributed evidence. All four are computable,
so none has to be asserted by hand.

### Outputs

Model each output kind with its own predicate rather than a generic "has output" plus a type, because
predicates are what the views and the diagram switch on. A workable set: article, dataset, software,
method, data-management plan, pre-registration, presentation, blog post, media coverage, social post,
podcast, discussion.

Watch for the failure mode where the outputs layer and the rest of the compendium drift apart: the
papers that evidence items cite as documentation must also be registered as outputs of the project,
or the Outputs box will show a subset that contradicts the Evidence box.

### People and institutions

One predicate per role. For people: principal investigator, project lead, data steward, participant.
For institutions: lead institution, partner, funder. Roles drive the sort order in every view (PI
first, lead institution before partner, funder last) and, if a deployment wants it, the membership
test for "was this published by someone on the project?".

A person may hold several roles; treat the *minimum* role rank as their sort key, not an arbitrary
one, or their position will jump between renderings.

## What the model deliberately does not do

- **It does not close the world.** Absence of evidence for a statement means nobody published any
  *that this compendium's query includes*, not that none exists.
- **It does not adjudicate.** Approval, checking and endorsement are separate assertions layered on
  top (see [views-and-actions.md](views-and-actions.md)); the compendium never infers that a claim is
  correct from the fact that it is present.
- **It does not require completeness.** Every layer is optional, and partial compendia are the normal
  case. A view that renders an empty band is more honest than one that hides the gap.

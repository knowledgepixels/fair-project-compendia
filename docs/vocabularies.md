# Vocabularies

Recommended terms, the alternatives that were considered, and why they were rejected. Prefixes used
below:

```turtle
@prefix obi:   <http://purl.obolibrary.org/obo/> .    # OBI_*, ECO_*, IAO_*, SEPIO_*
@prefix hycl:  <http://purl.org/petapico/o/hycl#> .
@prefix cito:  <http://purl.org/spar/cito/> .
@prefix prov:  <http://www.w3.org/ns/prov#> .
@prefix dct:   <http://purl.org/dc/terms/> .
@prefix schema: <https://schema.org/> .
@prefix disco: <http://rdf-vocabulary.ddialliance.org/discovery#> .
@prefix wd:    <https://www.wikidata.org/entity/> .
```

## Activities: OBI investigation

**Use `OBI_0000066` (investigation).** Its definition is domain-neutral — a planned process with the
objective of generating knowledge — and it pairs with `OBI_0500000` (study design) if a deployment
wants to record the design separately from its execution.

Direct subclasses of *investigation* worth offering in a picker:

| IRI | Label |
|---|---|
| `OBI_0000355` | hypothesis-driven investigation |
| `OBI_0000356` | hypothesis generating investigation |
| `OBI_0002897` | surveillance process |
| `OBI_0003692` | case-control investigation |
| `OBI_0003693` | observational investigation |
| `OBI_0003694` | longitudinal investigation |
| `OBI_0003695` | nested case-control investigation |
| `OBI_0003696` | animal investigation |
| `OBI_0003697` | clinical investigation |
| `OBI_0003698` | observational clinical investigation |
| `OBI_0003699` | clinical trial |
| `OBI_0003700`–`OBI_0003702` | phase I / II / III clinical trial |
| `OBI_0004001` / `OBI_0004002` | randomized / non-randomized clinical trial |

**How far OBI generalises.** Structurally it is domain-free, and its statistical design vocabulary
(observation vs. intervention, crossover, repeated measures, blocking) is classical design-of-
experiments that applies well beyond the life sciences. Its *coverage*, however, is overwhelmingly
molecular-biology assays: there is nothing for surveys, interviews, ethnography, simulation studies
beyond a bare "in silico design", or corpus work. Treat OBI as the typing backbone and accept that
non-biomedical deployments will use the generic class plus, where useful, a second type from
elsewhere.

### Rejected for activities

- **`schema.org`** has no generic `Study` class at all (`schema.org/Study` is a 404). It offers
  `MedicalStudy` with `MedicalTrial` and `MedicalObservationalStudy` subtypes, which are usable *in
  addition* to an OBI type when the work is medical. Note that `schema:ResearchProject` is not a
  candidate: it sits under `Organization`, so it denotes the enterprise, not an activity.
- **`disco:Study`** (DDI-RDF Discovery) is defined generically — "the process by which a data set was
  generated or collected" — and carries no social-science axioms, so it is safe to reuse. But the
  vocabulary around it assumes microdata: universe, instrument, variables, logical data set. It buys
  little over `obi:investigation` plus PROV unless a deployment actually uses that machinery.
- **`SIO`** covers study, hypothesis, procedure and measurement coherently but is heavyweight for this
  purpose.

## Evidence: ECO

**Use `ECO_0000000` (evidence) as the base type**, plus one of its nine direct subclasses:

| IRI | Label |
|---|---|
| `ECO_0000006` | experimental evidence |
| `ECO_0000041` | similarity evidence |
| `ECO_0000212` | combinatorial evidence |
| `ECO_0000352` | evidence used in manual assertion |
| `ECO_0000361` | inferential evidence |
| `ECO_0000501` | evidence used in automatic assertion |
| `ECO_0006055` | high throughput evidence |
| `ECO_0006151` | documented statement evidence |
| `ECO_0007672` | computational evidence |

Deeper subclasses are often a better fit — for example `ECO_0000044` (sequence similarity evidence).
Rather than enumerate thousands of terms, offer the nine top-level kinds directly and let contributors
search the whole subtree; see the OLS lookup recipe in [templates.md](templates.md).

There is deliberately **no locally minted evidence class**. An earlier draft introduced one and it
added nothing: ECO's root already means exactly "information interpreted as supporting an assertion",
and a local class would have to be maintained and mapped.

## Knowledge: HYCL

`hycl:AIDA-Sentence` for statements, and HYCL's relation set for connecting them:

`hasSameMeaning`, `hasDifferentMeaning`, `hasOppositeMeaning`, `hasNonoppositeMeaning`,
`hasConflictingMeaning`, `hasConsistentMeaning`, `hasMoreGeneralMeaningThan`,
`hasMoreSpecificMeaningThan`, `hasRelatedMeaning`, `hasUnrelatedMeaning`, `isImprovedVersionOf`.

`hycl:Formula` exists for formal statements and is the right type for a theorem, with an AIDA sentence
kept as the human-readable rendering.

HYCL also has work→statement relations (`claims`, `hypothesizes`, `investigates`, `refutes`,
`reviews`) which a deployment can use to attach statements to papers rather than to evidence.

## Support: CiTO and PROV

- `cito:obtainsSupportFrom` — statement → evidence (or → activity, or → publication).
- `cito:isDocumentedBy` — evidence → the output that reports it.
- `prov:wasGeneratedBy` — evidence → activity.
- `prov:wasAssociatedWith` — activity → person.
- `prov:wasAttributedTo` / `prov:wasDerivedFrom` — in the *provenance graph* of each nanopub, for who
  the assertion comes from and what it was derived from.

Keep the last pair straight: `wasAttributedTo` records whose claim this is, which is not the same as
who published the nanopub (`dct:creator`) and not at all the same as who verified it.

## Naming the evidence layer

The label matters more than it looks. "Evidence" alone is wrong for deductive work: in mathematics and
computer science, evidence means *heuristic* support — numerical checks, verified special cases — and
calling a proof "evidence" reads as a downgrade, implying the question is still open.

Options considered:

| Candidate | Verdict |
|---|---|
| **Evidence & Arguments** | **Recommended.** Covers empirical results, formal proofs (a proof is a deductive argument, matching SEPIO's definition of an evidence line) and humanities interpretation. |
| Grounds | Best single word: neutral across a historian's sources, a mathematician's proof and a philosopher's argument. Less familiar to biomedical readers. |
| Justification | Standard in epistemology, unambiguous, but long and slightly bureaucratic. |
| Support | **Avoid in FAIR deployments.** The FIP vocabulary already uses *FAIR Supporting Resources* and *FAIR-Enabling Resources*, so a "Support" box reads as supporting *resources* — tools, policies, services — rather than epistemic grounds. |
| Warrant | Wrong slot: in Toulmin's model the warrant licenses the inference, it is not the material. |
| Results / Demonstration / Derivations | Each too narrow for a mixed portfolio. |

## Formal proofs

Structurally a proof fits the model unchanged: generated by a theoretical activity, documented by an
article or a machine-checked formalisation (which the Outputs layer records as software), supporting a
statement. Epistemically it does not fit ECO, and there is **no proof or theorem class in ECO, IAO or
OBI** — checked. Recommended handling:

- type proofs `wd:Q11538` (mathematical proof) or `wd:Q2762418` (formal proof);
- consider a dedicated `proves` predicate alongside `obtainsSupportFrom`, since a proof establishes
  rather than merely supports;
- give the knowledge layer a third state ("proved") instead of stretching the first-evidence /
  increased-evidence scale, which encodes accumulation and does not apply to deduction;
- for machine-checked proofs, split them: the proof is `wd:Q2762418`, and "the checker accepted it" is
  a separate `ECO_0007672` computational evidence item.

## SEPIO: the two-tier alternative

SEPIO models this domain properly: `SEPIO_0000001` assertion ← `SEPIO_0000002` evidence line ←
`SEPIO_0000149` evidence item, with `has_evidence_line`, `has_evidence_item`,
`evidence_has_supporting_reference`, `evidence_direction` (values `SEPIO_0000403` supporting,
`SEPIO_0000404` disputing, `SEPIO_0000405` inconclusive) and `evidence_line_strength`. Its
`SEPIO_0000173` (study finding) is an excellent type for result items.

Its advantage is real: an *evidence line* is the reasoning step, so it can bundle several items, carry
strength, and — most valuably — record evidence that **disputes** a claim, which the flat model cannot
express.

Its cost is a second reification layer between statement and data, new templates for both the line and
the item, and treating each statement as a SEPIO assertion. The recommendation is to start flat and
upgrade only when strength or disagreement is actually needed: flat evidence items *are* SEPIO
evidence items, so lines can be layered on later without touching them.

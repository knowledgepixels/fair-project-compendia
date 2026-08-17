# Views and actions

Two kinds of view make up a compendium's interface: **project-level** views listing each layer, and
**part-level** views showing one entity in detail. Both are declared as nanopubs and activated per
project space with a display nanopub.

## Project-level views

One per layer, each a tabular view over a query parameterised by the project:

```turtle
sub:view a gen:ResourceView, gen:TabularView ;
    dct:isVersionOf sub:view-kind ;              # stable identity across versions
    dct:title "🔬 Activities" ;                  # emoji prefix, bare code point (see below)
    gen:appliesToInstancesOf gen:Space ;
    gen:hasStructuralPosition "4.6.activities" ; # controls order on the page
    gen:hasViewAction sub:addAction ;
    gen:hasViewQuery <…/get-project-activities> ;
    gen:hasViewQueryTargetField "project" .      # the query's placeholder receives the space IRI
```

Give each view an "➕ add…" action pointing at the corresponding template, with
`gen:hasActionTemplateTargetField` naming the template placeholder that should be pre-filled with the
page's resource. That single line is what turns a read-only compendium into one contributors can grow.

Structural positions are sorted as strings, so plan them: `4.5.outputs` sorts before `4.6.activities`
sorts before `4.7.findings`. Leaving gaps between numbers avoids renumbering later.

## Part-level views

A part page is `/part?id=<entity>&context=<space>`. Two facts govern whether a view appears on it:

1. **The context may be a space**, not only a maintained resource. Since view components append
   `&context=<page resource>` to internal links automatically, a `/part?id=…` link emitted by a view on
   a project page arrives with the right context. Link to `/part`, not to a generic explore page: the
   latter forwards to a part page only when a *maintained resource* declares the IRI's namespace.
2. **A view matches a part** when the part's IRI starts with one of the view's `gen:appliesToNamespace`
   values, **or** one of the part's `rdf:type`s is in its `gen:appliesToInstancesOf`.

So a detail view for evidence is declared:

```turtle
sub:view a gen:ResourceView, gen:TabularView ;
    dct:title "⚖ About this evidence" ;
    gen:appliesToInstancesOf obo:ECO_0000000 ;   # the PART's class, not a page type
    gen:hasStructuralPosition "3.1.evidenceInfo" ;
    gen:hasViewQuery <…/get-evidence-info> ;
    gen:hasViewQueryTargetField "evidence" .
```

The part's classes and label come from a *term-definition* lookup, which requires some nanopub to
**`npx:introduce`** the entity, signed by a member of the space. Consequences:

- entities the compendium introduces (activities, evidence, statements published as sentences) get
  class-gated detail views for free;
- entities that only ever appear as objects — DOIs, ORCIDs, ROR IRIs, and statements published only via
  relation nanopubs — have no classes, so they need **namespace-gated** views instead
  (`gen:appliesToNamespace <https://doi.org/>`, `<https://orcid.org/>`, `<http://purl.org/aida/>`, …).
  Namespace gating needs no data changes at all, which makes external identifiers as easy as local ones.

A part-level view still needs a **display** nanopub activating it on the space; the class or namespace
filter then decides which parts it appears on.

## Property/value tables

For a detail view, a one-row-many-columns table reads badly. Pivot it into key/value rows using this
column convention:

| Column | Role |
|---|---|
| `?Property_noheader` | the predicate IRI (left column); `_noheader` suppresses the column heading |
| `?Property_label` | its display label, e.g. `"Kind:"` |
| `?Value_multi_val_noheader` | the value(s), newline-separated; `_multi_val` marks a multi-valued cell |
| `?Value_label_multi` | labels for those values, so IRIs render as named links |

Generate the rows with a `values` block and pick each row's value with an `if` chain:

```sparql
values (?key ?Property_noheader ?Property_label) {
  ('Kind'   rdf:type            'Kind:')
  ('Desc'   dct:description     'Description:')
  ('Status' npx:approvesOf      'Status:')
  ('Source' dct:source          'Source:')
}
bind(if(?key = 'Kind', ?kind_vals,
     if(?key = 'Desc', str(?description),
     if(?key = 'Status', if(?isApproved, "approved", "not approved"), str(?np)))) as ?rawVal)
filter(bound(?rawVal) && ?rawVal != "")
order by (if(?key = 'Kind', 1, if(?key = 'Desc', 2, if(?key = 'Status', 3, 4))))
```

Rows whose value is absent drop out automatically, so the same view serves sparse and complete
entities. Put the source nanopub in the last row (`dct:source`), labelled with the nanopub's own title
rather than its Trusty URI.

Two column names are special and useful:

- a column literally named **`np`** (or `nps`) is never rendered; it becomes the row's "source" entry
  in the actions dropdown;
- any column referenced by an **action query mapping** is hidden automatically, so mapping columns can
  be returned without cluttering the table.

## Deriving status instead of asserting it

Approval is data, not a flag on the entity. Compute it in the query:

```sparql
bind(exists {
  graph npa:graph { ?anp npa:hasValidSignatureForPublicKeyHash ?apk ; np:hasAssertion ?aa .
    filter not exists { ?ainv npx:invalidates ?anp ; npa:hasValidSignatureForPublicKeyHash ?apk . }
    filter not exists { ?asup npx:supersedes ?anp . } }
  graph ?aa { ?approver npx:approvesOf ?np }
} as ?isApproved)
```

Use `EXISTS` inside `BIND`, not an `OPTIONAL` join: several approvals would otherwise multiply the
pivot's rows.

The same technique generalises. A "checked by a project participant" marker can be derived from
whether the asserting nanopub was published by an admin *and* its assertion is
`prov:wasAttributedTo` somebody holding a project role. Be careful what you claim it means, though:
attribution records where a claim came from, not that anyone verified it. If the marker is meant to
carry weight, derive it from an explicit endorsement nanopub instead — which is exactly what the
approval status above does.

## Actions: entry vs. result

This distinction is the single most important implementation detail on this page.

| | `gen:ViewEntryAction` | `gen:ViewResultAction` |
|---|---|---|
| Rendered | once per row | once per result |
| Query mapping | resolved **before** navigation, into real page parameters | forwarded to the publish form as `values-from-query` |
| `@raw` keys (`@override`, `@supersede`, `@derive-a`, `@template`) | **work** | **silently do nothing** |
| Value selection | this row's value | one value **per result row** |
| `gen:isVisibleTo` gating | honoured | honoured |

Two consequences that cost real debugging time:

**`@override` only works on an entry action.** The raw-key resolution lives in the entry-action path;
the result-action path hands the mapping to the publish form, which interprets it purely as template
parameters, while the fill mode is read from the `override`/`supersede`/`derive` *URL* parameters. An
`@override` on a result action therefore opens an **empty** form. Declare it as an entry action and
bind its mapping column on exactly the row where the button belongs — the source row.

**A result action collects one value per row.** With a pivoted seven-row table, a mapping like
`"target_np:nanopub"` handed the approval template seven identical values and the form opened with the
approval statement repeated seven times.

Control which rows carry a button by binding the mapping column conditionally — and note the two
conventions differ:

```sparql
# entry action: the button is hidden when its mapped value is empty
bind(if(?key = 'Status' && !?isApproved, str(?np), "") as ?approve_target)

# result action: an unbound value keeps the collected set to exactly one
bind(if(?key = 'Source', str(?np), ?nothing) as ?target_np)
```

`?nothing` is a variable that is never bound anywhere: referencing it makes the expression error, and
`BIND` then leaves the column unbound. That is SPARQL's idiom for a conditional bind.

Recommended action set for a detail view:

- **override** — entry action on the source row, template = the one that created the entity, mapping
  `"target_np:@override"`, gated `gen:isVisibleTo gen:MemberRole`. Override mode keeps the entity's
  introduced IRI and root definition, so editing does not re-mint identity.
- **approve** — entry action on the status row, the community approval template, mapping
  `"approve_target:nanopub"`, shown only while unapproved.

## Anchor-point actions in SVG views

Positioned actions inside a figure are possible today with no code change: emit an
`<a href="/publish?template=…&param_…=…">` around a shape, since `href` on `<a>` survives sanitisation
and the context parameter is appended automatically. A dropdown *at* an anchor is the expensive part —
it needs viewBox-to-CSS coordinate conversion and an absolutely positioned overlay. An intermediate
design is sentinel hrefs (`/action?key=…`) rewritten in the component's existing post-processing step,
with the actions declared on the view as usual; prefer path-like sentinels over `#fragment` ones given
the sanitiser's URL policy.

## Emoji in titles and labels

Use the **bare code point**, never followed by the `U+FE0F` variation selector. Check before signing:

```bash
grep -o '[^ ]*️[^ ]*' view.trig    # matches only if a selector is present
```

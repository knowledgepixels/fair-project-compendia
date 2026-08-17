# Templates

Assertion templates turn a compendium from something a curator hand-writes into something contributors
can extend through a form. A deployment needs at most four new templates; the rest already exist in the
nanopublication ecosystem and should be reused rather than re-minted.

## What to reuse

| Purpose | Existing template |
|---|---|
| Statement as an AIDA sentence, with topics | "Expressing a statement as an AIDA sentence" — no project field, right for general statements |
| Statement tied to a project | "Expressing a statement about research as an AIDA sentence" — same, plus a required project link |
| Relating two statements | "Asserting a relation between two statements" — restricted choice over all eleven HYCL relations, both operands regex-constrained to AIDA IRIs |
| Approving a nanopub | "Approving or disapproving of a nanopublication" — `npx:approvesOf` / `npx:disapprovesOf`, a Trusty-URI placeholder named `nanopub`, optional comment |
| Linking an output to a project | Whatever the deployment's project vocabulary already provides |

Before writing a template, list the current ones (`get-assertion-templates`) and search for the shape
you need. In this pattern's development, two templates that were about to be written already existed.

## What to create

### 1. Activity template

```turtle
sub:assertion a nt:AssertionTemplate ;
    rdfs:label "Defining a study" ;
    nt:hasNanopubLabelPattern "Study: ${title}" ;
    nt:hasTargetNanopubType obo:OBI_0000066 ;
    nt:hasStatement sub:st0, sub:st1, sub:st2, sub:st3, sub:st4, sub:st5 .

sub:activity  a nt:IntroducedResource, nt:LocalResource, nt:UriPlaceholder .   # short name → URI suffix
sub:subtype   a nt:RestrictedChoicePlaceholder ; nt:possibleValue … .          # OBI subclasses (+ schema.org medical types)
sub:title     a nt:LiteralPlaceholder .
sub:description a nt:LongLiteralPlaceholder .
sub:project   a nt:GuidedChoicePlaceholder ; nt:possibleValuesFromApi "…find-things?type=<project class>" .
sub:person    a nt:AgentPlaceholder .
sub:link      a nt:UriPlaceholder .

# st0: activity rdf:type obi:investigation          (fixed)
# st1: activity rdf:type ?subtype                   (optional, repeatable)
# st2: activity rdfs:label ?title
# st3: activity dct:description ?description        (optional)
# st4: activity dct:isPartOf ?project               (optional)
# st5: activity prov:wasAssociatedWith ?person      (optional, repeatable)
# st6: activity rdfs:seeAlso ?link                  (optional, repeatable)
```

Two details that matter in practice. Use `nt:AgentPlaceholder` for people rather than a plain URI
field, so contributors pick a known agent instead of pasting an ORCID. And **statement order in the
rendered form is the sort order of the statement IRIs** (`st0` < `st1` < …) unless `nt:statementOrder`
is set — so renumber, don't reorder.

### 2. Evidence template

Same shape, with `obo:ECO_0000000` as the fixed type, `prov:wasGeneratedBy` required (an evidence item
without an activity is orphaned) and `cito:isDocumentedBy` optional and repeatable.

For the kind field, combine a fixed list with live lookup so that contributors get the common cases
immediately and the whole subtree on demand:

```turtle
sub:kind a nt:GuidedChoicePlaceholder ;
    nt:possibleValue obo:ECO_0000006, obo:ECO_0000041, obo:ECO_0000212, obo:ECO_0000352,
      obo:ECO_0000361, obo:ECO_0000501, obo:ECO_0006055, obo:ECO_0006151, obo:ECO_0007672 ;
    nt:possibleValuesFromApi
      "https://www.ebi.ac.uk/ols/api/select?ontology=eco&allChildrenOf=http://purl.obolibrary.org/obo/ECO_0000000&q=" .
```

Three constraints hide in that one string:

- Use the **legacy `/ols/api/select` prefix**, not `/ols4/api/select`. Nanodash selects its OLS
  response parser by matching the API string against the legacy path; an `ols4` URL falls through to
  the generic JSON branch, which looks for `@id`/`concepturi`/`uri` and finds nothing, because OLS4
  returns `iri`. The legacy path redirects to OLS4 and returns the expected
  `response.docs[].iri/label/description` shape.
- `allChildrenOf` restricts results to the subtree, which is what makes a generic lookup usable.
- The search term is appended to the end of the string, hence the trailing `&q=`.

Also declare `rdfs:label` for every value you offer, in the template's assertion graph, or the form
shows bare ontology numbers.

### 3. Statement-relation usage (no new template)

Publish one nanopub per generality link, using the existing relation template. Because its single
statement is not repeatable, one nanopub carries one link — which is a feature: each link is separately
retractable, and a link is *not* a claim that either statement is true.

### 4. Output and role templates

Most deployments already have these. If not, keep them minimal: a kind picker (the predicate), the
output IRI, an optional title. Note that the *optional title* matters when the same resource is
described by more than one nanopub — see the label-consistency warning in
[publishing.md](publishing.md).

## Template versioning

Reference templates from views and actions by their **embedded template IRI** where the template
declares one, and give new templates a stable kind (`dct:isVersionOf` a kind IRI plus
`npx:introduces` on it) so later versions resolve automatically. A template published without a kind
forces every referencing view to be updated whenever the template changes.

# SPARQL cookbook

Querying nanopublications means querying an RDF4J store behind grlc, with the nanopub index in a
dedicated admin graph. Most of the entries below produce **wrong results rather than errors**, which is
what makes them expensive.

Prefixes assumed:

```sparql
prefix np:  <http://www.nanopub.org/nschema#>
prefix npa: <http://purl.org/nanopub/admin/>
prefix npx: <http://purl.org/nanopub/x/>
prefix gen: <https://w3id.org/kpxl/gen/terms/>
```

## The base pattern: a current, trusted nanopub

```sparql
graph npa:graph {
  ?np npa:hasValidSignatureForPublicKeyHash ?pk ;
      np:hasAssertion ?a ;
      np:hasPublicationInfo ?pi ;
      np:hasProvenance ?prov .
  filter not exists { ?inv npx:invalidates ?np ; npa:hasValidSignatureForPublicKeyHash ?pk . }
  filter not exists { ?sup npx:supersedes ?np . }
}
graph ?a { … the assertion you care about … }
```

Three parts, all necessary: a valid signature, no retraction *by the same key*, and no superseding
version. Omitting the last one is the usual cause of a view showing an entity twice with different
labels.

### `np:hasAssertion` lives in `npa:graph`

Querying `?np np:hasAssertion ?a` **without** the graph clause silently matches nothing, because the
default graph is not the union of all graphs here. This is the single most common cause of a query that
parses, runs fast and returns zero rows.

## Restricting to publishers you trust

A compendium should not show entries asserted by arbitrary third parties. Two ways:

**Space membership (federated).** Ask the spaces repository for the member keys, then filter:

```sparql
service <…/repo/spaces> {
  select (group_concat(?mpk; separator=" ") as ?memberPubkeys) where {
    graph npa:graph { <http://purl.org/nanopub/admin/thisRepo> npa:hasCurrentSpaceState ?stateG . }
    values ?_project_multi_iri {}
    graph ?stateG {
      ?_project_multi_iri npa:isMaintainedBy? ?space .
      ?ri a gen:RoleInstantiation ; npa:forSpace ?space ; npa:forAgent ?agent ; npa:hasRoleType ?roleType .
      filter(?roleType in (gen:AdminRole, gen:MaintainerRole, gen:MemberRole))
      ?acct a npa:AccountState ; npa:agent ?agent ; npa:pubkey ?mpk .
    }
  }
}
filter(contains(?memberPubkeys, ?pk))
```

**Project roles (local).** Cheaper, no federation, and often what you actually mean — require the
nanopub's `dct:creator` to hold a role in the project:

```sparql
graph ?ma { ?project ?mrel ?member .
  values ?mrel { gen:hasAdmin gen:hasProjectLead <role predicates…> } }
graph ?pi { ?np dct:creator ?member ; dct:created ?created . }
```

Prefer the local form inside nested subqueries: a federated `SERVICE` there is slow enough to hit a
504.

## Picking one nanopub per entity

```sparql
{
  select ?np where {
    values ?_entity_multi_iri {}          # ← repeat the values clause HERE, see below
    … base pattern + membership …
    graph ?pi { ?np dct:created ?created }
  } order by desc(?created) limit 1
}
```

## Traps

### 1. A subquery cannot see the outer `values`

Subqueries are evaluated bottom-up. A `values ?_x_multi_iri {}` in the outer query does **not**
constrain an inner `select`, so the inner query runs unbound — typically returning the globally latest
entity of that type instead of the requested one. Repeat the `values` clause inside every subquery that
needs it; grlc substitutes all occurrences.

The same applies to any pattern that is not inside the subquery: if a ranking copy of a pattern lives in
an `OPTIONAL` next to a subquery, it needs its own `values` clause or it will match *other projects*
and inflate the results.

### 2. `FILTER` scope is the group it appears in

A filter inside a `UNION` arm or a nested group cannot see variables bound outside that group.
`filter(contains(?memberPubkeys, ?pk))` placed inside a union arm always fails, so the arm returns
nothing — silently. Either lift the filter to the level where the variable is bound, or (for unions)
put the `SERVICE` that binds it **inside each arm**.

`FILTER` inside `OPTIONAL` is the exception: it may reference outer variables, because it is the join
condition.

### 3. A `SERVICE` next to a `UNION` corrupts the federated request

With a `SERVICE` and a `UNION` as siblings in the same group, RDF4J mis-serialises the outgoing query
and the endpoint answers HTTP 500 with a lexical error mentioning a truncated `PREFIX`. Put the
`SERVICE` inside each union arm — which also solves trap 2 for free.

### 4. A `FILTER` after a sub-`SELECT` inside `OPTIONAL` is ignored

```sparql
optional {
  { select ?o (min(?r) as ?rank) where { … } group by ?o }
  filter(?rank < ?myRank)          # ← NOT applied
}
```

RDF4J does not treat this filter as the join condition, so every row matches and counts come out as
"all of them". Keep the ranking copy a **flat** pattern inside the `OPTIONAL` and put the comparison in
that optional's filter.

### 5. A `graph ?g { … }` block containing only an `OPTIONAL` returns nothing

```sparql
graph ?a { optional { ?x a ?kind . filter(?kind != …) } }     # 0 rows
optional { graph ?a { ?x a ?kind } filter(?kind != …) }       # correct
```

Always wrap the graph in the optional, not the other way round.

### 6. An unbound variable in a later `OPTIONAL` matches anything

If one optional leaves `?kind` unbound and a later optional does `graph ?pi { ?kind rdfs:label ?l }`,
that second optional will happily bind `?kind` to *any* labelled subject in the pubinfo graph. The
result is a cross product with labels from unrelated resources. Nest dependent lookups inside the
optional that binds their subject:

```sparql
optional {
  graph ?a { ?x a ?kind }
  filter(?kind != …)
  optional { graph ?pi { ?kind rdfs:label ?kind_label } }
}
```

### 7. Ranking without window functions

SPARQL 1.1 has no `ROW_NUMBER`. To position items, count how many same-group items sort earlier:

```sparql
{
  select ?item (min(?label) as ?lbl) (min(?rr) as ?rank) (count(distinct ?other) as ?index) where {
    … items binding ?item, ?label, ?rr (a role rank) …
    optional {
      … the SAME pattern binding ?other, ?orr …
      filter(concat(str(?orr), "|", str(?other)) < concat(str(?rank_of_item), "|", str(?item)))
    }
  } group by ?item
}
```

Compose the sort key as `"<rank>|<iri>"` so a role ordering (PI first, funder last) beats alphabetical
order while staying deterministic. Pre-group the left side so an entity holding several roles sorts by
its *best* role; the right side can stay flat, because `count(distinct ?other)` counts an entity once if
any of its rows sorts earlier — which is the same as using its minimum.

### 8. Multi-row queries and action mappings

An action query mapping takes one value **per result row**. For a pivoted table that means a repeated
form field; bind the mapping column on a single row only (see
[views-and-actions.md](views-and-actions.md)).

### 9. grlc placeholder naming

`?_x_iri` is substituted **inline**, so `values ?_x_iri {}` becomes `values <iri> {}` → malformed
query. Only the `_multi_iri` infix fills a `VALUES` clause: use `?_x_multi_iri`, and the corresponding
view field name is still `"x"`.

### 10. Test with POST

A long query in a GET URL fails with "Request header is too large". Always
`curl -X POST … --data-urlencode "query@file.rq"`.

## Debugging method

When a query returns nothing or too much, bisect it mechanically rather than by inspection:

1. run the innermost subquery alone, with the parameter substituted by hand;
2. add one block at a time, checking the row count after each;
3. when a count changes unexpectedly, you have found the block — and it is usually one of traps 1–6.

Keep the intermediate `.rq` files. Every trap above was found this way, and several of them look
perfectly correct on the page.

# Publishing, identity and versioning

The rules here are the difference between a compendium that stays coherent as it is edited and one whose
links quietly rot.

## Keep introduced IRIs stable

When you publish a new version of a nanopub that **introduces** a resource, reference that resource by
its **original absolute IRI** and keep `npx:introduces` pointing at it:

```turtle
sub:pubinfo {
  this: npx:introduces <https://w3id.org/np/RA-ORIGINAL-TRUSTY/my-entity> ;
        npx:supersedes  <https://w3id.org/np/RA-PREVIOUS-TRUSTY> .
}
sub:assertion {
  <https://w3id.org/np/RA-ORIGINAL-TRUSTY/my-entity> a … ; rdfs:label "…" .
}
```

Do **not** write `sub:my-entity` in a superseding version: that resolves against the *new* nanopub's
namespace and mints a different entity, orphaning the old one and breaking every inbound link. A
supersede is a new version of a *statement*, not a new *thing*. Nanodash's **override** fill mode exists
for exactly this and preserves the introduced IRIs; the equivalent when hand-authoring is the absolute
IRI above.

Getting this wrong is recoverable but expensive: every nanopub that referenced the old IRI has to be
republished, and if any of those are themselves referenced, the churn cascades.

If you expect an entity to be edited, consider minting it under a project-owned namespace
(`…/r/evidence/<slug>`) rather than as a sub-IRI of the nanopub that happens to introduce it. Sub-IRIs
are fine but tie identity to a nanopub; a project namespace also lets a maintained-resource declaration
give the entity a part page in its own right.

## Version identity for views, queries and templates

Give any nanopub that others reference a **stable kind**:

```turtle
sub:thing  dct:isVersionOf <https://w3id.org/np/RA-ORIGINAL/thing-kind> .
this:      npx:introduces  <https://w3id.org/np/RA-ORIGINAL/thing-kind> ;
           npx:supersedes  <https://w3id.org/np/RA-PREVIOUS> .
```

Always re-introduce the **original** kind IRI, never a fresh one. Display activations then keep pointing
at the same kind and resolve to the latest version, so a view can be revised without republishing its
displays — in practice this saves eight display nanopubs per revision in an eight-project deployment.

A view that references a query by its nanopub URI must be republished whenever that query changes.
Expect the pair to move together, and keep a note of which query version each view version points at.

## Timestamps

Use the **exact current UTC time**:

```bash
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

A timestamp equal to the registry clock to the second publishes fine. Do not invent a backdated
cadence: a session that stamps everything an hour or two early produces a record that misstates when
things were made, which is both wrong and hard to repair later.

The one real constraint is that the registry rejects **future** timestamps, with a misleading
`400 … Nanopublication not supported` and no clue about the cause. Signing and validation pass; only
publishing fails. Diagnose by comparing to the registry's own clock:

```bash
curl -sI https://<registry>/ | grep -i '^date'
```

A stamp 22 minutes ahead was rejected in testing, so the tolerance is small; exact-now is comfortably
inside it. If clock skew ever bites, subtract a minute or two — not hours.

## String escaping when embedding SPARQL in TriG

A query embedded in `grlc:sparql """…"""` must survive TriG unescaping. Two independent hazards:

1. **`\n` inside the query.** A `separator="\n"` written as-is becomes a real newline when the TriG is
   parsed, breaking the SPARQL string literal — the endpoint reports a lexical error mentioning
   character 10. Escape backslashes first, then quotes:

   ```python
   esc = q.replace('\\', '\\\\').replace('"', '\\"')
   ```

2. **`re.sub` interprets backslashes in its replacement string.** Substituting the escaped query into a
   TriG file with `re.sub(pattern, 'grlc:sparql """' + esc + '""" .', text)` silently halves the
   escaping. Use a function replacement:

   ```python
   text = re.sub(pattern, lambda m: 'grlc:sparql """' + esc + '""" .', text, flags=re.S)
   ```

Then **verify by round-tripping** — extract the literal back out of the TriG, unescape it, and compare
with the original query text before signing:

```python
lit = re.search(r'grlc:sparql """(.*?)""" \.', trig, re.S).group(1)
assert unescape(lit) == query
```

This check costs three lines and catches a class of bug whose only other symptom is a published,
permanently broken nanopub.

## A publish checklist

1. Sign, then **verify the artefact**, not the intention: for a query, run the extracted SPARQL against
   the endpoint; for a view, render it; for a diagram, parse the SVG and check its geometry.
2. Check the timestamp is now, not invented.
3. Check emoji have no `U+FE0F` variation selector.
4. Check labels are consistent with any other nanopub describing the same resource — two different
   labels for one IRI make view output nondeterministic, because queries pick one with `sample()` or
   `min()` (see also [naming.md](naming.md)). If a second nanopub must repeat a label, repeat it *identically*; if it does not need to,
   omit it and let the original stand.
5. After publishing, confirm the nanopub resolves on the registry and that the API serving it returns
   what you expect. Publication succeeding is not evidence that the content is right.

## Being honest about propagation

A freshly published nanopub is not immediately visible everywhere: the registry accepts it first, the
query service indexes it after, and interface caches expire later still. When something does not appear,
distinguish the three before changing anything — and note that the query service can also simply be
degraded, returning 500s or connection-pool timeouts for queries that worked minutes earlier. Re-run a
known-good query to tell a service problem from your own.

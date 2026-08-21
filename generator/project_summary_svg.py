#!/usr/bin/env python3
"""Generates the SPARQL query behind a project compendium's summary SVG view.

Configure the CONFIG block below for your deployment: the target render width, and one
entry per layer giving its assertion pattern, type expression, icon expression and column
count. Everything else -- panel widths, truncation caps, panel heights, arrow placement,
the ranking joins -- is derived. See ../docs/svg-diagram.md.

Usage:  python3 project_summary_svg.py > query.rq

Natural viewBox coordinates rendered at SCALE. The declared width equals the host
panel width, so the figure fills the column 1:1 and text lands at the page's own
size; declaring a larger width also renders (CSS max-width:100% scales it down)
but then the text comes out smaller than the surrounding body text.

Emoji icons render monochrome because the SVG uses Nanodash's own font stack
with the bundled "Noto Emoji" webfont first. That font's unicode-range covers
only emoji code points, so Latin text still falls through to Inter; without it,
font-family="sans-serif" would resolve emoji via the system colour-emoji font.

Entries are left-aligned: "<icon> <label>" inside the <a>, and the type/role in a
sibling <tspan dx=...> immediately after it -- still inside the same <text>, so
text flow places it exactly where the label ends, but outside the <a>, so it keeps
the normal text colour instead of the page's link colour.

Each zone is one aggregate subquery. Items are pre-grouped per IRI (so an item
holding several roles gets its minimum role rank), and the vertical index comes
from a self-join counting same-zone items with a smaller sort key. That key is
"<role rank>|<iri>", which is what puts the PI before the participants and the
lead institution before the funder.

Every zone truncates its label to the column width minus that row's type text, so
nothing can overflow; the full text stays in the <title> tooltip.
"""

import re

# ---------------------------------------------------------------- CONFIG ----
# The project vocabulary this deployment uses. Only these IRIs are
# deployment-specific; replace them with your own predicate set.
FF = "https://w3id.org/fair/ff/terms/"      # namespace whose has-* predicates carry outputs and roles
# minted for deductive grounds; both are inert for deployments that publish no proofs
PROVES = "https://w3id.org/np/RApY2x9ZrKtmpsW-ZINc1M1cvI9LYbmZ1-Gbgl3TEJsCI/proves"
PROOF_TYPE = "wd:Q11538"                    # wikidata "mathematical proof", see docs/vocabularies.md

PREFIXES = """prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
prefix dct: <http://purl.org/dc/terms/>
prefix np: <http://www.nanopub.org/nschema#>
prefix npa: <http://purl.org/nanopub/admin/>
prefix npx: <http://purl.org/nanopub/x/>
prefix gen: <https://w3id.org/kpxl/gen/terms/>
prefix ff: <https://w3id.org/fair/ff/terms/>
prefix obo: <http://purl.obolibrary.org/obo/>
prefix hycl: <http://purl.org/petapico/o/hycl#>
prefix cito: <http://purl.org/spar/cito/>
prefix foaf: <http://xmlns.com/foaf/0.1/>
prefix prov: <http://www.w3.org/ns/prov#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix wd: <http://www.wikidata.org/entity/>"""

MEMBERS = """          service <https://w3id.org/np/l/nanopub-query-1.1/repo/spaces> {
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
          }"""


def valid(s, pi=True, member=True):
    pi_line = f"\n              np:hasPublicationInfo ?pi{s} ;" if pi else ""
    mf = f"\n          filter(contains(?memberPubkeys, ?pk{s}))" if member else ""
    return f"""          graph npa:graph {{
            ?np{s} np:hasAssertion ?a{s} ;{pi_line}
              npa:hasValidSignatureForPublicKeyHash ?pk{s} .
            filter not exists {{ ?ix{s} npx:invalidates ?np{s} ; npa:hasValidSignatureForPublicKeyHash ?pk{s} . }}
            filter not exists {{ ?sx{s} npx:supersedes ?np{s} . }}
          }}{mf}"""


OUT_ICON = (
    'if(?rawSFX = "article", "\U0001F4C4", if(?rawSFX = "software", "\U0001F4BB",'
    ' if(?rawSFX = "dataset", "\U0001F4BE", if(?rawSFX = "presentation", "\U0001F3A4",'
    ' if(?rawSFX = "blog-post", "\U0001F4DD", if(?rawSFX = "podcast", "\U0001F3A7",'
    ' if(?rawSFX = "media-coverage", "\U0001F4F0", if(?rawSFX = "social-post", "\U0001F4AC",'
    ' if(?rawSFX = "discussion", "\U0001F4AC", if(?rawSFX = "method", "\U0001F527",'
    ' if(?rawSFX = "dmp", "\U0001F4CB", "\U0001F517")))))))))))'
)
EV_ICON = ('if(?typeSFX = "proof", "\U0001F4D0",'
           ' if(contains(?typeSFX, "combinatorial"), "\U0001F9E9",'
           ' if(contains(?typeSFX, "similarity"), "\U0001F9EC",'
           ' if(contains(?typeSFX, "computational"), "\U0001F5A5",'
           ' if(contains(?typeSFX, "documented"), "\U0001F4D1",'
           ' if(contains(?typeSFX, "high throughput"), "\U0001F9EB",'
           ' if(contains(?typeSFX, "inferential"), "\U0001F9E0", "\U0001F50E")))))))')
ACT_ICON = ('if(contains(?typeSFX, "observational"), "\U0001F441",'
            ' if(contains(?typeSFX, "surveillance"), "\U0001F4E1",'
            ' if(contains(?typeSFX, "trial"), "\U0001F489", "\U0001F9EA")))')
KNO_ICON = ('if(?typeSFX = "proved", "\U0001F4D0",'
            ' if(?typeSFX = "first evidence", "\U0001F331", "\U0001F4C8"))')
OUT_RANK = ('if(?rawSFX = "article", 0, if(?rawSFX = "dataset", 1, if(?rawSFX = "software", 2,'
            ' if(?rawSFX = "method", 3, if(?rawSFX = "dmp", 4, if(?rawSFX = "presentation", 5,'
            ' if(?rawSFX = "blog-post", 6, 7)))))))')
PPL_TYPE = ('if(?relSFX = ff:has-principal-investigator, "PI",'
            ' if(?relSFX in (gen:hasProjectLead, ff:has-project-leader), "project lead",'
            ' if(?relSFX = ff:has-data-steward, "data steward", "participant")))')
PPL_RANK = ('if(?relSFX = ff:has-principal-investigator, 0,'
            ' if(?relSFX in (gen:hasProjectLead, ff:has-project-leader), 1,'
            ' if(?relSFX = ff:has-data-steward, 2, 3)))')
INST_TYPE = ('if(?relSFX = ff:has-lead-institution, "lead institution",'
             ' if(?relSFX = ff:has-partner-institution, "partner", "funder"))')
INST_RANK = ('if(?relSFX = ff:has-lead-institution, 0,'
             ' if(?relSFX = ff:has-partner-institution, 1, 2))')
INST_ICON = 'if(?relSFX = ff:has-funder, "\U0001F4B6", "\U0001F3DB")'

PAT = {
    "act": "ITEM a obo:OBI_0000066 ; dct:isPartOf ?_project_multi_iri .",
    "out": ("?_project_multi_iri ?relSFX ITEM .\n            values ?relSFX { ff:has-article ff:has-dataset"
            " ff:has-software ff:has-method ff:has-dmp ff:has-presentation ff:has-blog-post"
            " ff:has-media-coverage ff:has-social-post ff:has-podcast ff:has-discussion }"),
    "ppl": ("?_project_multi_iri ?relSFX ITEM .\n            values ?relSFX { ff:has-principal-investigator"
            " ff:has-participant ff:has-data-steward gen:hasProjectLead ff:has-project-leader }"),
    "inst": ("?_project_multi_iri ?relSFX ITEM .\n            values ?relSFX { ff:has-lead-institution"
             " ff:has-partner-institution ff:has-funder }"),
}

# Nanodash renders the figure at PANEL_W; SCALE keeps 10-unit text at ~16px (12pt body text)
PANEL_W, SCALE = 1395, 1.6   # target render width in px, and natural-units-to-px scale
                             # 10 units of text * SCALE should equal the host page's body size
# measured average advance widths of Inter at these sizes (label 10px, type 9px)
LABEL_CW, TYPE_CW = 5.15, 4.6
CANVAS = int(PANEL_W / SCALE)          # natural width
MARGIN_, ARROWGAP_, PADX_, COLGAP_ = 10, 32, 12, 16
CONTENT = CANVAS - 2 * MARGIN_          # widest box, outer
FULLCOL = CONTENT - 2 * PADX_           # single-column content width


def _col(cols, gap_total=None):
    """Column width so that `cols` columns fill the full content width."""
    gaps = (cols - 1) * COLGAP_ if gap_total is None else gap_total
    return (FULLCOL - gaps) // cols


# zone -> column width, type expr, icon expr, columns, caption icon
ZCFG = {
    "kno": (FULLCOL, None, KNO_ICON, 1, "\U0001F4A1"),
    "ev": (_col(2), None, EV_ICON, 2, "\u2696"),
    # the middle pair shares the content width with an arrow channel between the boxes
    "act": ((CONTENT - ARROWGAP_) // 2 - 2 * PADX_, None, ACT_ICON, 1, "\U0001F52C"),
    "out": ((CONTENT - ARROWGAP_) // 2 - 2 * PADX_, 'replace(?rawSFX, "-", " ")', OUT_ICON, 1, "\U0001F4E6"),
    "ppl": (_col(4), PPL_TYPE, '"\U0001F464"', 4, "\U0001F465"),
    "inst": (_col(2), INST_TYPE, INST_ICON, 2, "\U0001F3DB"),
}
RANKS = {"ppl": PPL_RANK, "inst": INST_RANK, "out": OUT_RANK}
PITCH = {}                   # every zone uses DEFAULT_PITCH now
DEFAULT_PITCH = 20
COLGAP, PADX = COLGAP_, PADX_
# knowledge line lengths in characters, derived from the column width; the type
# follows the LAST line, so only that line reserves room for it
# both lines reserve room for the type, since a sentence that fits on one line
# keeps its type on that same line
KNO_CAP2 = int((FULLCOL - 26 - len("increased evidence") * TYPE_CW) / LABEL_CW)
KNO_CAP1 = KNO_CAP2

# -------------------------------------------------------------- /CONFIG ----
# Nothing below is deployment-specific: box widths, truncation caps, box heights,
# arrow placement and the ranking joins all derive from the values above.

DECODE = ('replace(replace(replace(replace(replace(strafter(str(ITEM), "http://purl.org/aida/"),'
          ' "[+]", " "), "%2C", ","), "%3A", ":"), "%28", "("), "%29", ")")')


def items(s, item, with_meta=True, member=True):
    """The zone's assertion pattern; with_meta adds the label/type/icon/rank binds."""
    _w, type_expr, icon_expr, _c, _ci = ZCFG[s]
    rank = RANKS.get(s, "0").replace("SFX", s)
    ic = icon_expr.replace("SFX", s)
    ty = (type_expr or '""').replace("SFX", s)

    if s == "kno":
        # only the higher-level statements: those that generalise one of the project's findings
        # Two ways a statement earns a place: it generalises one of the project's findings,
        # or a proof generated by one of the project's studies establishes it. The support
        # hop is one step (finding -> study) or two (finding -> evidence -> study); both
        # shapes occur in the wild, so two sibling optionals + a coalesce filter accept
        # either. They must be SIBLINGS, not nested: a valid() block inside a nested
        # OPTIONAL never binds under RDF4J. Both key on ?anchor, which the core always
        # binds, so neither can cross-product the way an unbound-subject OPTIONAL would.
        # Expressed as a predicate alternation with an inverse path rather than a UNION:
        # a SERVICE anywhere near a UNION mis-serialises the federated request (HTTP 500),
        # even with the SERVICE inside each arm. One flat pattern keeps a single SERVICE.
        core = f"""{MEMBERS if member else ""}
{valid('sg' + s, pi=False, member=member)}
          graph ?asg{s} {{
            ?studyg{s} a obo:OBI_0000066 ; dct:isPartOf ?_project_multi_iri .
          }}
{valid('rg' + s, pi=False, member=member)}
          graph ?arg{s} {{
            {item} (hycl:hasMoreGeneralMeaningThan|^<{PROVES}>) ?anchor{s} .
          }}
          optional {{
{valid('fg' + s, pi=False, member=member)}
            graph ?afg{s} {{ ?anchor{s} a hycl:AIDA-Sentence ; cito:obtainsSupportFrom ?sup{s} . }}
          }}
          optional {{
{valid('hg' + s, pi=False, member=member)}
            graph ?ahg{s} {{ ?anchor{s} cito:obtainsSupportFrom ?mid{s} . }}
{valid('eg' + s, pi=False, member=member)}
            graph ?aeg{s} {{ ?mid{s} prov:wasGeneratedBy ?via{s} . }}
          }}
          optional {{
{valid('qg' + s, pi=False, member=member)}
            graph ?aqg{s} {{ ?anchor{s} prov:wasGeneratedBy ?pst{s} . }}
          }}
          filter(coalesce(?sup{s} = ?studyg{s}, false) || coalesce(?via{s} = ?studyg{s}, false)
                 || coalesce(?pst{s} = ?studyg{s}, false))"""
        meta = f"""          optional {{
{valid('og' + s, pi=False, member=False)}
            graph ?aog{s} {{ {item} hycl:hasMoreGeneralMeaningThan ?ofnd{s} . }}
{valid('pg' + s, pi=False, member=False)}
            graph ?apg{s} {{ ?ofnd{s} skos:related ?oproj{s} . }}
            filter(?oproj{s} != ?_project_multi_iri)
          }}
          bind({DECODE.replace('ITEM', item)} as ?label{s})
          optional {{
{valid('pv' + s, pi=False, member=False)}
            graph ?apv{s} {{ ?anyproof{s} <{PROVES}> {item} . }}
          }}
          bind(if(bound(?anyproof{s}), "proved",
                  if(bound(?oproj{s}), "increased evidence", "first evidence")) as ?type{s})
          bind(0 as ?rr{s})
          bind({ic} as ?icon{s})"""
        return core + "\n" + (meta if with_meta else f"          bind(0 as ?rr{s})")

    if s == "ev":
        core = f"""{valid('s' + s, pi=False, member=member)}
          graph ?as{s} {{
            ?study{s} a obo:OBI_0000066 ; dct:isPartOf ?_project_multi_iri .
          }}
{valid(s, member=member)}
          graph ?a{s} {{
            {item} a ?base{s} ; prov:wasGeneratedBy ?study{s} .
            values ?base{s} {{ obo:ECO_0000000 {PROOF_TYPE} }}
          }}"""
        meta = f"""          optional {{ graph ?a{s} {{ {item} rdfs:label ?la{s} }} }}
          optional {{
            graph ?a{s} {{
              {item} a ?sub{s} .
              filter(?sub{s} != obo:ECO_0000000 && strstarts(str(?sub{s}), "http://purl.obolibrary.org/obo/ECO_"))
            }}
            graph ?pi{s} {{ ?sub{s} rdfs:label ?subl{s} }}
          }}
          bind(coalesce(?la{s}, replace(str({item}), "^.*[/#]", "")) as ?label{s})
          bind(coalesce(?subl{s}, if(?base{s} = {PROOF_TYPE}, "proof", "evidence")) as ?type{s})
          bind(0 as ?rr{s})
          bind({ic} as ?icon{s})"""
    elif s == "act":
        core = f"""{valid(s, member=member)}
          graph ?a{s} {{
            {PAT['act'].replace('ITEM', item)}
          }}"""
        meta = f"""          optional {{ graph ?a{s} {{ {item} rdfs:label ?la{s} }} }}
          optional {{
            graph ?a{s} {{
              {item} a ?sub{s} .
              filter(?sub{s} != obo:OBI_0000066 && strstarts(str(?sub{s}), "http://purl.obolibrary.org/obo/OBI_"))
            }}
            graph ?pi{s} {{ ?sub{s} rdfs:label ?subl{s} }}
          }}
          bind(coalesce(?la{s}, replace(str({item}), "^.*[/#]", "")) as ?label{s})
          bind(coalesce(replace(?subl{s}, "investigation", "study"), "study") as ?type{s})
          bind(0 as ?rr{s})
          bind({ic} as ?icon{s})"""
    else:
        core = f"""{valid(s, member=member)}
          graph ?a{s} {{
            {PAT[s].replace('ITEM', item).replace('SFX', s)}
          }}"""
        raw = (f'          bind(strafter(str(?rel{s}), "{FF}has-") as ?raw{s})\n' if s == "out" else "")
        meta = f"""          optional {{ graph ?a{s} {{ {item} rdfs:label ?la{s} }} }}
          optional {{ graph ?pi{s} {{ {item} foaf:name ?lf{s} }} }}
          optional {{ graph ?pi{s} {{ {item} rdfs:label ?lq{s} }} }}
          bind(coalesce(?la{s}, ?lf{s}, ?lq{s}, replace(str({item}), "^.*[/#]", "")) as ?label{s})
{raw}          bind({ty} as ?type{s})
          bind({rank} as ?rr{s})
          bind({ic} as ?icon{s})"""

    if with_meta:
        return core + "\n" + meta
    # ranking copy: only the sort key is needed, but "out" still needs ?raw for its icon expr
    tail = (f'          bind(strafter(str(?rel{s}), "{FF}has-") as ?raw{s})\n' if s == "out" else "")
    return core + "\n" + tail + f"          bind({rank} as ?rr{s})"


def others(s):
    """The same items, renamed, used only to rank each entry."""
    t = items(s, "?o" + s, with_meta=False, member=False)
    for v in ("np", "a", "pi", "pk", "ix", "sx", "rel", "raw", "study", "as", "sub", "subl",
              "la", "lf", "lq", "lp", "fnd", "studyg", "asg", "afg", "arg",
              # knowledge-zone support chain and evidence-zone base type
              "anchor", "sup", "via", "pst", "base", "aeg", "aqg", "ahg", "mid",
              "nphg", "pkhg", "ixhg", "sxhg",
              "npeg", "pkeg", "ixeg", "sxeg", "npqg", "pkqg", "ixqg", "sxqg",
              "nps", "pks", "ixs", "sxs", "npsg", "pksg", "ixsg", "sxsg",
              "npfg", "pkfg", "ixfg", "sxfg", "nprg", "pkrg", "ixrg", "sxrg", "rr"):
        t = t.replace("?" + v + s, "?o" + v + s)
    return t


def zone(s):
    w, _t, _i, cols, _ci = ZCFG[s]
    pitch = PITCH.get(s, DEFAULT_PITCH)
    two_line = False       # knowledge entries are single-line too, truncated with "…"
    avail = f"({w} - 26 - strlen(?typ{s}) * {TYPE_CW})"
    cap = f"xsd:integer(floor({avail} / {LABEL_CW}))"

    link = f"'<a href=\"/part?id=', encode_for_uri(str(?iri{s})), '\">'"
    if two_line:
        one = (f"""concat('<text x="', str(?bx{s}), '" y="', str(?by{s} + 10), '" font-size="10" fill="#111">',
          {link}, '<title>', ?full{s}, '</title><tspan>', ?ico{s}, '  ', ?l1{s}, '</tspan></a>',
          '<tspan dx="9" font-size="9">', ?typ{s}, '</tspan></text>')""")
        two = (f"""concat('<text x="', str(?bx{s}), '" y="', str(?by{s} + 10), '" font-size="10" fill="#111">',
          {link}, '<title>', ?full{s}, '</title><tspan>', ?ico{s}, '  ', ?l1{s}, '</tspan></a></text>',
        '<text x="', str(?bx{s} + 14), '" y="', str(?by{s} + 21), '" font-size="10" fill="#111">',
          {link}, '<tspan>', ?l2{s}, '</tspan></a>',
          '<tspan dx="9" font-size="9">', ?typ{s}, '</tspan></text>')""")
        frag = f'if(?l2{s} = "", {one}, {two})'
        wrap = f"""      bind(if(strlen(?esc{s}) > {KNO_CAP1}, replace(?esc{s}, "^(.{{1,{KNO_CAP1}}})[ ].*$", "$1"), ?esc{s}) as ?l1{s})
      bind(if(strlen(?esc{s}) > strlen(?l1{s}), substr(?esc{s}, strlen(?l1{s}) + 2, {KNO_CAP2}), "") as ?l2{s})"""
        label_expr = f"?lbl{s}"
    else:
        frag = (f"""concat('<text x="', str(?bx{s}), '" y="', str(?by{s} + 12), '" font-size="10" fill="#111">',
          {link}, '<title>', ?full{s}, '</title><tspan>', ?ico{s}, '  ', ?esc{s}, '</tspan></a>',
          '<tspan dx="9" font-size="9">', ?typ{s}, '</tspan></text>')""")
        wrap = ""
        label_expr = f'if(strlen(?lbl{s}) > ?cap{s}, concat(substr(?lbl{s}, 1, ?cap{s} - 1), "…"), ?lbl{s})'

    # the ranking copy carries its own pubkey variables; each must belong to a space member,
    # and each is bound()-guarded because a UNION arm binds only its own
    oth = others(s)
    keys = sorted(set(re.findall(r"\?opk\w*", oth)))
    mcheck = "".join(f"\n              && (!bound({k}) || contains(?mpk{s}, {k}))" for k in keys)

    return f"""  {{
    select (group_concat(distinct ?box{s}; separator="") as ?boxes{s}) (count(*) as ?n{s}) where {{
      {{
        select ?iri{s} ?lbl{s} ?ico{s} ?typ{s} ?rrank{s} (count(distinct ?o{s}) as ?iy{s}) where {{
          values ?_project_multi_iri {{}}
          {{
            select ?iri{s} (min(?label{s}) as ?lbl{s}) (min(?icon{s}) as ?ico{s})
                (group_concat(distinct ?type{s}; separator=", ") as ?typ{s}) (min(?rr{s}) as ?rrank{s})
                (sample(?memberPubkeys) as ?mpk{s}) where {{
              values ?_project_multi_iri {{}}
{"" if s == "kno" else MEMBERS}
{items(s, '?iri' + s)}
            }} group by ?iri{s}
          }}
          optional {{
{oth}
            filter(concat(str(?orr{s}), "|", str(?o{s})) < concat(str(?rrank{s}), "|", str(?iri{s})){mcheck})
          }}
        }} group by ?iri{s} ?lbl{s} ?ico{s} ?typ{s} ?rrank{s}
      }}
      bind((?iy{s} - floor(?iy{s} / {cols}) * {cols}) * {w + COLGAP} as ?bx{s})
      bind(floor(?iy{s} / {cols}) * {pitch} as ?by{s})
      bind({cap} as ?cap0{s})
      bind(if(?cap0{s} < 8, 8, ?cap0{s}) as ?cap{s})
      bind({label_expr} as ?t{s})
      bind(replace(replace(replace(?t{s}, "&", "&amp;"), "<", "&lt;"), ">", "&gt;") as ?esc{s})
      bind(replace(replace(replace(?lbl{s}, "&", "&amp;"), "<", "&lt;"), ">", "&gt;") as ?full{s})
{wrap}
      bind({frag} as ?box{s})
    }}
  }}"""


# ---- layout (natural coordinates; rendered at SCALE) -----------------------
MARGIN, ARROWGAP = MARGIN_, ARROWGAP_


def gw(s):
    w, _t, _i, cols, _ci = ZCFG[s]
    return cols * w + (cols - 1) * COLGAP


def bw(s):
    return gw(s) + 2 * PADX


# the middle row is now just activities and outputs, side by side
MIDW = bw("act") + bw("out") + ARROWGAP
W = max(MIDW, bw("kno"), bw("ev"), bw("ppl"), bw("inst")) + 2 * MARGIN
CENTER = W // 2
COLS = {"act": CENTER - MIDW // 2, "out": CENTER + MIDW // 2 - bw("out")}
A1 = COLS["act"] + bw("act")


def rows(s, n):
    cols = ZCFG[s][3]
    return f"floor(({n} + {cols - 1}) / {cols})"


HK = f"({rows('kno', '?nkno')} * {PITCH.get('kno', DEFAULT_PITCH)} + 14)"
HE = f"({rows('ev', '?nev')} * {DEFAULT_PITCH} + 14)"
HM = f"((if(?nact > ?nout, ?nact, ?nout)) * {DEFAULT_PITCH} + 14)"
HP = f"({rows('ppl', '?nppl')} * {DEFAULT_PITCH} + 14)"
HI = f"({rows('inst', '?ninst')} * {DEFAULT_PITCH} + 14)"
YK = "26"
YE = f"(26 + {HK} + 28)"
YM = f"({YE} + {HE} + 28)"
YP = f"({YM} + {HM} + 26)"
YI = f"({YP} + {HP} + 26)"
TOTAL = f"({YI} + {HI} + 12)"
MIDY = f"({YM} + {HM} / 2)"


def caption(x, y, text, icon):
    return (f"""'<text x="{x}" y="', str({y}), '" font-size="11" """
            f"""font-weight="bold" fill="#444">{icon}  {text}</text>',""")


def zonebox(x, y, w, h):
    return (f"""'<rect x="{x}" y="', str({y}), '" width="{w}" height="', str({h}),
      '" rx="4" fill="#f4f4f4" stroke="#888"></rect>',""")


def group(x, y, var):
    return f"""'<g transform="translate({x},', str({y}), ')">', {var}, '</g>',"""


def zone_svg(s, box_x, y, h, cap_text, cap_x=None):
    return (f"""{caption(box_x + PADX, f"{y} - 8", cap_text, ZCFG[s][4])}
    {zonebox(box_x, y, bw(s), h)}
    {group(box_x + PADX, f"{y} + 6", '?boxes' + s)}""")


ARROW, ARROW_SIZE = "\u27A4", 22
ARROW_NUDGE = round(0.315 * ARROW_SIZE)   # U+27A4 ink centre sits 0.315em above the baseline                     # black rightwards arrowhead, rendered as text
ACT_CX = COLS["act"] + bw("act") // 2
OUT_CX = COLS["out"] + bw("out") // 2
ARROW_CX = (COLS["act"] + bw("act") + COLS["out"]) // 2   # centre of the arrow channel


def arrow_right(x, y):
    return (f"""'<text x="{x}" y="', str({y} + {ARROW_NUDGE}), '" text-anchor="middle" font-size="{ARROW_SIZE}" """
            f"""fill="#888">{ARROW}</text>',""")


def arrow_up(x, y):
    """The same glyph, rotated a quarter turn counter-clockwise. Vertical centring is
    exact (rotation keeps the baseline midpoint), horizontal needs the +5 nudge."""
    ax = x + ARROW_NUDGE
    return (f"""'<text x="{ax}" y="', str({y}), '" text-anchor="middle" font-size="{ARROW_SIZE}" fill="#888" """
            f"""transform="rotate(-90 {ax} ', str({y}), ')">{ARROW}</text>',""")


SVG = f"""    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} ', str({TOTAL}),
      '" width="{int(W * SCALE)}" height="', str(round(({TOTAL}) * 8 / 5)), '" font-family="Noto Emoji, Inter, Verdana, Helvetica, sans-serif">',
    {zone_svg('kno', CENTER - bw('kno') // 2, YK, HK, "Knowledge", CENTER)}
    {zone_svg('ev', CENTER - bw('ev') // 2, YE, HE, "Evidence &amp; Arguments", CENTER)}
    {zone_svg('act', COLS['act'], YM, HM, "Activities")}
    {zone_svg('out', COLS['out'], YM, HM, "Outputs")}
    {zone_svg('ppl', CENTER - bw('ppl') // 2, YP, HP, "People", CENTER)}
    {zone_svg('inst', CENTER - bw('inst') // 2, YI, HI, "Institutions", CENTER)}
    {arrow_right(ARROW_CX, MIDY)}
    {arrow_up(ACT_CX, f"{YM} - 14")}
    {arrow_up(OUT_CX, f"{YM} - 14")}
    {arrow_up(CENTER, f"{YE} - 14")}
    {arrow_up(ACT_CX, f"{YP} - 13")}
    '</svg>'"""

QUERY = f"""{PREFIXES}
select (concat(
{SVG}) as ?svg)
where {{
{zone('kno')}
{zone('ev')}
{zone('act')}
{zone('out')}
{zone('ppl')}
{zone('inst')}
}}"""

if __name__ == "__main__":
    print(QUERY)

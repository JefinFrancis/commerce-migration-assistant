#!/usr/bin/env python3
"""Render a read-only HTML review report from a Canonical Commerce Model.

The report is a PURE VIEW of ccm.json — never a source of truth. Edits happen to
the JSON (by hand or by asking Claude); the report is regenerated on demand. Output
is a single self-contained HTML file (inline CSS + a little vanilla JS, no external
requests) that opens with a double-click.

Usage:
    python3 reporters/render.py <ccm.json> --phase analysis|plan --out report.html
"""

import argparse
import html
import json
import os

# CCM top-level entity -> (commercetools concept, Terraform resource).
CT_TARGET = {
    "productTypes": ("Product Type", "commercetools_product_type"),
    "categories": ("Category", "commercetools_category"),
    "customFieldTypes": ("Type (custom fields)", "commercetools_type"),
    "customerGroups": ("Customer Group", "commercetools_customer_group"),
    "taxCategories": ("Tax Category", "commercetools_tax_category"),
    "zones": ("Zone", "commercetools_shipping_zone"),
    "shippingMethods": ("Shipping Method", "commercetools_shipping_method"),
    "channels": ("Channel", "commercetools_channel"),
    "stores": ("Store", "commercetools_store"),
    "productSelections": ("Product Selection", "commercetools_product_selection"),
    "businessUnits": ("Business Unit", "commercetools_business_unit_company / _division"),
    "associateRoles": ("Associate Role", "commercetools_associate_role"),
    "attributeGroups": ("Attribute Group", "commercetools_attribute_group"),
    "states": ("State", "commercetools_state"),
    "customObjects": ("Custom Object", "commercetools_custom_object"),
}
ENTITY_LABEL = {k: v[0] for k, v in CT_TARGET.items()}


def _esc(value):
    return html.escape(str(value), quote=True)


def _plain(localized, default=""):
    if isinstance(localized, str):
        return localized
    if isinstance(localized, dict):
        return localized.get("en") or next(iter(localized.values()), default)
    return default


def _load_css():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "report.css")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "body{font-family:system-ui;margin:2rem;}"  # minimal fallback


def _origin_badge(origin):
    origin = origin or "source"
    return '<span class="badge %s">%s</span>' % (_esc(origin), _esc(origin))


def _confidence(conf):
    if conf is None:
        return '<span class="conf"><span class="v">—</span></span>'
    cls = "good" if conf >= 0.85 else ("warn" if conf >= 0.7 else "bad")
    pct = int(round(conf * 100))
    return (
        '<span class="conf %s"><span class="bar"><i style="width:%d%%"></i></span>'
        '<span class="v">%.2f</span></span>' % (cls, pct, conf)
    )


# --------------------------------------------------------------------------- #
# decisions
# --------------------------------------------------------------------------- #

def _iter_elements(ccm):
    """Yield (context, element) for every provenanced element in the CCM."""
    for key, target in ENTITY_LABEL.items():
        for el in ccm.get(key, []) or []:
            ctx = "%s / %s" % (target, _plain(el.get("name"), el.get("key", "")))
            yield ctx, el
            for attr in el.get("attributes", []) or []:
                yield "%s.%s" % (ctx, attr.get("name", "")), attr
            for field in el.get("fields", []) or []:
                yield "%s.%s" % (ctx, field.get("name", "")), field


def _collect_decisions(ccm):
    out = []
    for ctx, el in _iter_elements(ccm):
        for d in el.get("decisionsNeeded", []) or []:
            if not d.get("resolved"):
                out.append((ctx, d))
    return out


# --------------------------------------------------------------------------- #
# analysis phase
# --------------------------------------------------------------------------- #

def _attr_row(attr):
    type_desc = _esc(attr.get("type", ""))
    if attr.get("elementType"):
        type_desc += " &lt;%s&gt;" % _esc(attr["elementType"])
    if attr.get("referenceTypeId"):
        type_desc += " → %s" % _esc(attr["referenceTypeId"])
    level = attr.get("level", "")
    req = '<span class="tag">required</span>' if attr.get("required") else ""
    decision = "★" if attr.get("decisionsNeeded") else ""
    haystack = _esc((attr.get("name", "") + " " + (attr.get("origin") or "")).lower())
    return (
        '<tr data-search="%s" data-decision="%s">'
        '<td class="name">%s %s</td>'
        '<td class="lvl-%s">%s</td>'
        '<td>%s</td><td>%s</td><td>%s</td><td>%s</td>'
        '<td class="src">%s</td></tr>'
        % (
            haystack, "1" if attr.get("decisionsNeeded") else "0",
            _esc(attr.get("name", "")), decision,
            _esc(level), _esc(level),
            type_desc, req, _origin_badge(attr.get("origin")),
            _confidence(attr.get("confidence")),
            _esc(attr.get("sourceRef", "")),
        )
    )


def _product_type_card(pt):
    rows = "".join(_attr_row(a) for a in pt.get("attributes", []) or [])
    dnote = ""
    if pt.get("decisionsNeeded"):
        dnote = ' <span class="tag" style="color:var(--warn)">decision</span>'
    return (
        '<div class="pt"><h3>%s <span class="key">%s</span> %s%s</h3>'
        '<div class="tbl-wrap"><table><thead><tr>'
        '<th>Attribute</th><th>Level</th><th>Type</th><th></th>'
        '<th>Origin</th><th>Confidence</th><th>Source</th>'
        '</tr></thead><tbody>%s</tbody></table></div></div>'
        % (_esc(_plain(pt.get("name"), pt.get("key", ""))), _esc(pt.get("key", "")),
           _origin_badge(pt.get("origin")), dnote, rows)
    )


def _render_analysis(ccm):
    pts = ccm.get("productTypes", []) or []
    attrs = [a for pt in pts for a in pt.get("attributes", []) or []]
    decisions = _collect_decisions(ccm)
    confs = [a["confidence"] for a in attrs if isinstance(a.get("confidence"), (int, float))]
    avg = (sum(confs) / len(confs)) if confs else 0
    origins = {"source": 0, "domain-pack": 0, "manual": 0}
    for a in attrs:
        origins[a.get("origin", "source")] = origins.get(a.get("origin", "source"), 0) + 1

    tiles = "".join(
        '<div class="tile"><div class="n">%s</div><div class="l">%s</div></div>' % (n, l)
        for n, l in [
            (len(pts), "Product types"),
            (len(attrs), "Attributes"),
            (len(decisions), "Decisions needed"),
            ("%.2f" % avg, "Avg confidence"),
            ("%d / %d / %d" % (origins["source"], origins["domain-pack"], origins["manual"]),
             "source / domain / manual"),
        ]
    )

    parts = ['<div class="tiles">%s</div>' % tiles]

    if decisions:
        items = "".join(
            '<div class="decision"><div class="ctx">%s</div>'
            '<div class="q">%s</div>%s</div>'
            % (
                _esc(ctx), _esc(d.get("question", "")),
                ('<div class="opts">options: %s%s</div>' % (
                    _esc(", ".join(d.get("options", []))),
                    (" · recommended: %s" % _esc(d["recommendation"])) if d.get("recommendation") else "",
                )) if d.get("options") or d.get("recommendation") else "",
            )
            for ctx, d in decisions
        )
        parts.append('<div class="panel decisions"><h2>Decisions needed (%d)</h2>%s</div>'
                     % (len(decisions), items))

    parts.append(
        '<div class="toolbar">'
        '<input type="search" id="q" placeholder="Filter attributes by name or origin…">'
        '<label><input type="checkbox" id="donly"> Decisions only</label></div>'
    )
    parts.append("".join(_product_type_card(pt) for pt in pts))

    for key in ("categories", "customerGroups", "businessUnits", "associateRoles"):
        rows = ccm.get(key) or []
        if not rows:
            continue
        trs = "".join(
            '<tr><td class="name">%s</td><td>%s</td><td>%s</td><td class="src">%s</td></tr>'
            % (_esc(r.get("key", "")), _origin_badge(r.get("origin")),
               _confidence(r.get("confidence")), _esc(r.get("sourceRef", "")))
            for r in rows
        )
        parts.append(
            '<div class="panel"><h2>%s (%d)</h2><div class="tbl-wrap"><table><thead><tr>'
            '<th>Key</th><th>Origin</th><th>Confidence</th><th>Source</th></tr></thead>'
            '<tbody>%s</tbody></table></div></div>' % (_esc(ENTITY_LABEL[key]), len(rows), trs)
        )

    parts.append('<p class="note">Read-only view of <code>ccm.json</code>. '
                 'Edit the model and regenerate this report to update it.</p>')
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# plan phase
# --------------------------------------------------------------------------- #

def _render_plan(ccm):
    rows, tiles_data = [], []
    for key, (concept, tf) in CT_TARGET.items():
        items = ccm.get(key) or []
        if not items:
            continue
        manual = sum(1 for i in items if i.get("origin") == "manual")
        badge = ' <span class="badge manual">%d manual</span>' % manual if manual else ""
        rows.append(
            '<tr><td class="name">%s</td><td>%s</td><td class="tf">%s</td>'
            '<td>%d%s</td></tr>' % (_esc(key), _esc(concept), _esc(tf), len(items), badge)
        )
        tiles_data.append((len(items), concept + "s"))

    tiles = "".join(
        '<div class="tile"><div class="n">%s</div><div class="l">%s</div></div>' % (n, l)
        for n, l in tiles_data
    )
    table = (
        '<div class="panel"><h2>CCM → commercetools → Terraform</h2><div class="tbl-wrap">'
        '<table><thead><tr><th>CCM entity</th><th>commercetools</th>'
        '<th>Terraform resource</th><th>Count</th></tr></thead><tbody>%s</tbody></table>'
        '</div></div>' % "".join(rows)
    )
    return (
        '<div class="tiles">%s</div>%s'
        '<p class="note">"What <code>terraform apply</code> will create", derived from '
        '<code>ccm.json</code>. Read-only — regenerate after editing the model.</p>'
        % (tiles, table)
    )


# --------------------------------------------------------------------------- #

_SCRIPT = """
(function(){
  var q=document.getElementById('q'), donly=document.getElementById('donly');
  function apply(){
    var term=(q&&q.value||'').toLowerCase(), dec=donly&&donly.checked;
    document.querySelectorAll('tr[data-search]').forEach(function(tr){
      var okT=!term||tr.getAttribute('data-search').indexOf(term)>=0;
      var okD=!dec||tr.getAttribute('data-decision')==='1';
      tr.classList.toggle('hidden', !(okT&&okD));
    });
  }
  if(q) q.addEventListener('input', apply);
  if(donly) donly.addEventListener('change', apply);
})();
"""


def render(ccm, phase):
    meta = ccm.get("meta", {}) or {}
    if phase == "plan":
        title = "Migration Plan — CCM → commercetools"
        body = _render_plan(ccm)
    else:
        title = "Migration Mapping — Analysis"
        body = _render_analysis(ccm)
    meta_line = " · ".join(
        filter(None, [
            meta.get("client"), meta.get("domain"),
            "source: %s" % meta["sourcePlatform"] if meta.get("sourcePlatform") else None,
            "by %s" % meta["generatedBy"] if meta.get("generatedBy") else None,
        ])
    )
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>%s</title><style>\n%s\n</style></head><body>"
        "<header class=\"rpt\"><h1>%s</h1><div class=\"meta\">%s</div></header>"
        "<div class=\"wrap\">%s</div><script>%s</script></body></html>\n"
        % (_esc(title), _load_css(), _esc(title), _esc(meta_line), body, _SCRIPT)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a read-only HTML migration report from a CCM.")
    parser.add_argument("ccm", help="Path to ccm.json.")
    parser.add_argument("--phase", choices=["analysis", "plan"], default="analysis")
    parser.add_argument("--out", default=None, help="Output HTML path (default: reports/<phase>-report.html).")
    args = parser.parse_args(argv)

    with open(args.ccm, encoding="utf-8") as fh:
        ccm = json.load(fh)
    out = args.out or ("mapping-report.html" if args.phase == "analysis" else "plan-report.html")
    html_text = render(ccm, args.phase)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    print("Wrote %s (%s phase)" % (out, args.phase))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Emit Terraform (HCL) for the labd/commercetools provider from a CCM document.

Reads a Canonical Commerce Model (ccm.json) and renders HCL modules grouped by
resource family. Homogeneous resources (categories, customer groups) use
`for_each` over a data map (architecture §10); product types — whose nested
attribute schema is heterogeneous — are emitted as explicit generated blocks.

Usage:
    python3 emitters/terraform/emit.py <ccm.json> --out-dir <terraform/>
"""

import argparse
import json
import os
import re

DEFAULT_PROVIDER_VERSION = "~> 1.20"

# CCM attribute type -> labd/commercetools product-type attribute type name.
_TYPE_NAME = {
    "text": "text", "ltext": "ltext", "number": "number", "boolean": "boolean",
    "money": "money", "date": "date", "datetime": "datetime", "time": "time",
    "enum": "enum", "lenum": "lenum", "reference": "reference", "set": "set",
    "nested": "nested",
}
_CONSTRAINT = {"unique": "Unique", "combinationUnique": "CombinationUnique", "none": "None"}


class Writer:
    """Minimal indentation-aware HCL line writer."""

    def __init__(self):
        self.lines = []
        self.level = 0

    def line(self, text=""):
        self.lines.append(("  " * self.level + text) if text else "")

    def open(self, head):
        self.line(head + " {")
        self.level += 1

    def close(self):
        self.level -= 1
        self.line("}")

    def __str__(self):
        return "\n".join(self.lines).rstrip("\n") + "\n"


def _ident(key):
    """Sanitize a CCM key into a valid HCL resource local name."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", key or "")
    if not s or not re.match(r"[A-Za-z_]", s):
        s = "_" + s
    return s


def _esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _plain(localized, default=""):
    """A plain string from a CCM localizedString (string or locale map)."""
    if isinstance(localized, str):
        return localized
    if isinstance(localized, dict):
        return localized.get("en") or next(iter(localized.values()), default)
    return default


def _localized_inline(localized, fallback=""):
    """Render a CCM localizedString as an inline HCL map: { en = "x" }."""
    if isinstance(localized, dict) and localized:
        pairs = ", ".join('%s = "%s"' % (k, _esc(v)) for k, v in localized.items())
        return "{ %s }" % pairs
    return '{ en = "%s" }' % _esc(_plain(localized, fallback))


# --------------------------------------------------------------------------- #
# versions.tf
# --------------------------------------------------------------------------- #

def versions_tf(ccm):
    version = (ccm.get("meta") or {}).get("providerVersion") or DEFAULT_PROVIDER_VERSION
    w = Writer()
    w.open("terraform")
    w.open("required_providers")
    w.open("commercetools =")
    w.line('source  = "labd/commercetools"')
    w.line('version = "%s"' % version)
    w.close()
    w.close()
    w.close()
    return str(w)


# --------------------------------------------------------------------------- #
# product-types.tf  (explicit generated blocks)
# --------------------------------------------------------------------------- #

def _emit_enum_values(attr, w, localized):
    for value in attr.get("values", []):
        if localized:
            w.open("localized_value")
            w.line('key   = "%s"' % value["key"])
            w.line("label = %s" % _localized_inline(value.get("label"), value["key"]))
            w.close()
        else:
            w.open("value")
            w.line('key   = "%s"' % value["key"])
            w.line('label = "%s"' % _esc(_plain(value.get("label"), value["key"])))
            w.close()


def _emit_element_type(attr, w):
    elem = attr.get("elementType", "text")
    name = _TYPE_NAME.get(elem, "text")
    if name == "reference":
        w.line('name              = "reference"')
        w.line('reference_type_id = "%s"' % attr.get("referenceTypeId", ""))
    elif name in ("enum", "lenum"):
        w.line('name = "%s"' % name)
        _emit_enum_values(attr, w, localized=(name == "lenum"))
    else:
        w.line('name = "%s"' % name)


def _emit_type(attr, w):
    ccm_type = attr.get("type", "text")
    name = _TYPE_NAME.get(ccm_type, "text")
    w.open("type")
    if name == "set":
        w.line('name = "set"')
        w.open("element_type")
        _emit_element_type(attr, w)
        w.close()
    elif name == "reference":
        w.line('name              = "reference"')
        w.line('reference_type_id = "%s"' % attr.get("referenceTypeId", ""))
    elif name in ("enum", "lenum"):
        w.line('name = "%s"' % name)
        _emit_enum_values(attr, w, localized=(name == "lenum"))
    else:
        w.line('name = "%s"' % name)
    w.close()


def _emit_attribute(attr, w):
    w.open("attribute")
    w.line('name  = "%s"' % attr["name"])
    w.line("label = %s" % _localized_inline(attr.get("label"), attr["name"]))
    if attr.get("required"):
        w.line("required = true")
    constraint = attr.get("constraint")
    if constraint and constraint != "none":
        w.line('constraint = "%s"' % _CONSTRAINT.get(constraint, "None"))
    _emit_type(attr, w)
    w.close()


def product_types_tf(product_types):
    w = Writer()
    for i, pt in enumerate(product_types):
        if i:
            w.line()
        w.open('resource "commercetools_product_type" "%s"' % _ident(pt["key"]))
        w.line('key  = "%s"' % pt["key"])
        w.line('name = "%s"' % _esc(_plain(pt.get("name"), pt["key"])))
        if pt.get("description"):
            w.line('description = "%s"' % _esc(_plain(pt["description"])))
        for attr in pt.get("attributes", []):
            _emit_attribute(attr, w)
        w.close()
    return str(w)


# --------------------------------------------------------------------------- #
# categories.tf / customer-groups.tf  (for_each over a data map)
# --------------------------------------------------------------------------- #

def categories_tf(categories):
    w = Writer()
    w.open("locals")
    w.open("categories =")
    for cat in categories:
        parent = cat.get("parent")
        parent_hcl = 'null' if parent in (None, "") else '"%s"' % parent
        w.line(
            '%s = { name = "%s", slug = "%s", parent = %s }'
            % (_ident(cat["key"]), _esc(_plain(cat.get("name"), cat["key"])),
               _esc(_plain(cat.get("slug"), cat["key"])), parent_hcl)
        )
    w.close()
    w.close()
    w.line()
    w.open('resource "commercetools_category" "this"')
    w.line("for_each = local.categories")
    w.line("key  = each.key")
    w.line("name = { en = each.value.name }")
    w.line("slug = { en = each.value.slug }")
    w.line(
        "parent = each.value.parent != null ? "
        "commercetools_category.this[each.value.parent].id : null"
    )
    w.close()
    return str(w)


def customer_groups_tf(customer_groups):
    w = Writer()
    w.open("locals")
    w.open("customer_groups =")
    for group in customer_groups:
        w.line('%s = "%s"' % (_ident(group["key"]), _esc(_plain(group.get("name"), group["key"]))))
    w.close()
    w.close()
    w.line()
    w.open('resource "commercetools_customer_group" "this"')
    w.line("for_each = local.customer_groups")
    w.line("key  = each.key")
    w.line("name = each.value")
    w.close()
    return str(w)


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #

def emit(ccm):
    """Return {filename: hcl_text} for every resource family present in the CCM."""
    files = {"versions.tf": versions_tf(ccm)}
    if ccm.get("productTypes"):
        files["product-types.tf"] = product_types_tf(ccm["productTypes"])
    if ccm.get("categories"):
        files["categories.tf"] = categories_tf(ccm["categories"])
    if ccm.get("customerGroups"):
        files["customer-groups.tf"] = customer_groups_tf(ccm["customerGroups"])
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Emit Terraform HCL from a CCM document.")
    parser.add_argument("ccm", help="Path to a ccm.json document.")
    parser.add_argument("--out-dir", default="terraform", help="Directory to write .tf files into.")
    args = parser.parse_args(argv)

    with open(args.ccm, encoding="utf-8") as fh:
        ccm = json.load(fh)
    files = emit(ccm)
    os.makedirs(args.out_dir, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
    print("Wrote %d file(s) to %s: %s" % (len(files), args.out_dir, ", ".join(sorted(files))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""CLI entry point for the ATG codebase analyzer.

Deterministically parses an ATG repository-definition XML file and emits a
Canonical Commerce Model fragment (JSON). Invoked by the atg-codebase-analyzer
agent / analyze-atg skill.

Usage:
    python3 adapters/atg/analyze.py <repository.xml> [--client NAME] [--domain D] [--out ccm.json]
"""

import argparse
import json
import sys

from db_extract import parse_ddl
from extract import parse_repository
from to_ccm import build_ccm


def analyze(xml_path, client="Unknown", domain="", db_path=None):
    inventory = parse_repository(xml_path)
    db_inventory = parse_ddl(db_path) if db_path else None
    meta = {
        "client": client,
        "domain": domain,
        "sourcePlatform": "atg",
        "schemaVersion": "0.1.0",
        "generatedBy": "atg-codebase-analyzer" + ("+atg-database-analyzer" if db_inventory else ""),
    }
    return build_ccm(inventory, meta, db_inventory), inventory, db_inventory


def _summary(ccm, inventory, db_inventory=None):
    n_desc = len(inventory["itemDescriptors"])
    n_pt = len(ccm["productTypes"])
    n_attrs = sum(len(pt.get("attributes", [])) for pt in ccm["productTypes"])
    n_dec = sum(len(pt.get("decisionsNeeded", [])) for pt in ccm["productTypes"]) + sum(
        len(a.get("decisionsNeeded", []))
        for pt in ccm["productTypes"]
        for a in pt.get("attributes", [])
    )
    db_note = ""
    if db_inventory:
        n_dbonly = sum(
            1
            for pt in ccm["productTypes"]
            for a in pt.get("attributes", [])
            if a.get("sourceRef", "").count(".") and ":" not in a.get("sourceRef", "")
        )
        db_note = " Reconciled against %d DB tables (%d DB-only columns surfaced)." % (
            len(db_inventory["tables"]),
            n_dbonly,
        )
    return (
        "ATG analysis: %d item-descriptors -> %d product types, %d attributes, "
        "%d decisions to review.%s" % (n_desc, n_pt, n_attrs, n_dec, db_note)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze an ATG repository-definition file into a CCM fragment.")
    parser.add_argument("input", help="Path to an ATG repository-definition XML file.")
    parser.add_argument("--client", default="Unknown")
    parser.add_argument("--domain", default="")
    parser.add_argument("--db", default=None, help="Optional ATG GSA schema DDL to reconcile against.")
    parser.add_argument("--out", default=None, help="Write CCM JSON here (default: stdout).")
    args = parser.parse_args(argv)

    ccm, inventory, db_inventory = analyze(
        args.input, client=args.client, domain=args.domain, db_path=args.db
    )
    text = json.dumps(ccm, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("Wrote %s" % args.out, file=sys.stderr)
    else:
        print(text)
    print(_summary(ccm, inventory, db_inventory), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

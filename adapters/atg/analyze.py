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

from extract import parse_repository
from to_ccm import build_ccm


def analyze(xml_path, client="Unknown", domain=""):
    inventory = parse_repository(xml_path)
    meta = {
        "client": client,
        "domain": domain,
        "sourcePlatform": "atg",
        "schemaVersion": "0.1.0",
        "generatedBy": "atg-codebase-analyzer",
    }
    return build_ccm(inventory, meta), inventory


def _summary(ccm, inventory):
    n_desc = len(inventory["itemDescriptors"])
    n_pt = len(ccm["productTypes"])
    n_attrs = sum(len(pt.get("attributes", [])) for pt in ccm["productTypes"])
    n_dec = sum(len(pt.get("decisionsNeeded", [])) for pt in ccm["productTypes"]) + sum(
        len(a.get("decisionsNeeded", []))
        for pt in ccm["productTypes"]
        for a in pt.get("attributes", [])
    )
    return (
        "ATG codebase analysis: %d item-descriptors -> %d product types, "
        "%d attributes, %d decisions to review." % (n_desc, n_pt, n_attrs, n_dec)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze an ATG repository-definition file into a CCM fragment.")
    parser.add_argument("input", help="Path to an ATG repository-definition XML file.")
    parser.add_argument("--client", default="Unknown")
    parser.add_argument("--domain", default="")
    parser.add_argument("--out", default=None, help="Write CCM JSON here (default: stdout).")
    args = parser.parse_args(argv)

    ccm, inventory = analyze(args.input, client=args.client, domain=args.domain)
    text = json.dumps(ccm, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("Wrote %s" % args.out, file=sys.stderr)
    else:
        print(text)
    print(_summary(ccm, inventory), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

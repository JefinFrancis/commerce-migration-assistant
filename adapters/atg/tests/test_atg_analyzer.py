"""Tests for the deterministic ATG codebase analyzer.

Run from the repo root:
    python3 -m unittest discover -s adapters/atg/tests
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ATG_DIR = os.path.abspath(os.path.join(HERE, ".."))
REPO_ROOT = os.path.abspath(os.path.join(ATG_DIR, "..", ".."))
sys.path.insert(0, ATG_DIR)

import extract  # noqa: E402
import to_ccm  # noqa: E402
from analyze import analyze  # noqa: E402

FIXTURE = os.path.join(ATG_DIR, "fixtures", "productCatalog.xml")
SCHEMA = os.path.join(REPO_ROOT, "ccm", "schema", "ccm.schema.json")


def _attr(product_type, name):
    for a in product_type["attributes"]:
        if a["name"] == name:
            return a
    return None


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.inv = extract.parse_repository(FIXTURE)
        self.by_name = {d["name"]: d for d in self.inv["itemDescriptors"]}

    def test_finds_all_descriptors(self):
        self.assertEqual(
            set(self.by_name), {"product", "sku", "category", "warrantyPlan"}
        )

    def test_scalar_property(self):
        props = {p["name"]: p for p in self.by_name["product"]["properties"]}
        self.assertEqual(props["displayName"]["dataType"], "string")
        self.assertTrue(props["displayName"]["required"])
        self.assertFalse(props["featured"]["required"])

    def test_enumerated_options_parsed(self):
        props = {p["name"]: p for p in self.by_name["sku"]["properties"]}
        self.assertEqual(props["color"]["dataType"], "enumerated")
        values = [o["value"] for o in props["color"]["enumOptions"]]
        self.assertEqual(values, ["black", "white", "blue"])

    def test_multivalued_and_reference(self):
        props = {p["name"]: p for p in self.by_name["product"]["properties"]}
        self.assertTrue(props["keywords"]["multiValued"])
        self.assertEqual(props["keywords"]["componentDataType"], "string")
        self.assertTrue(props["relatedProducts"]["multiValued"])
        self.assertEqual(props["relatedProducts"]["componentItemType"], "product")


class ToCcmTests(unittest.TestCase):
    def setUp(self):
        self.ccm, _, _ = analyze(FIXTURE, client="Test Telco", domain="telecom")
        self.pts = {pt["key"]: pt for pt in self.ccm["productTypes"]}

    def test_product_and_sku_merge_into_one_product_type(self):
        self.assertIn("product", self.pts)
        pt = self.pts["product"]
        # product-level attribute from `product` descriptor
        self.assertEqual(_attr(pt, "displayName")["level"], "product")
        self.assertEqual(_attr(pt, "displayName")["type"], "text")
        # variant-level attribute from `sku` descriptor
        self.assertEqual(_attr(pt, "color")["level"], "variant")
        self.assertEqual(_attr(pt, "color")["type"], "enum")

    def test_type_mappings(self):
        pt = self.pts["product"]
        self.assertEqual(_attr(pt, "launchDate")["type"], "datetime")
        self.assertEqual(_attr(pt, "featured")["type"], "boolean")
        self.assertEqual(_attr(pt, "storageGb")["type"], "number")
        # scalar collection -> set of text
        kw = _attr(pt, "keywords")
        self.assertEqual(kw["type"], "set")
        self.assertEqual(kw["elementType"], "text")
        # item collection -> set of reference
        rel = _attr(pt, "relatedProducts")
        self.assertEqual(rel["type"], "set")
        self.assertEqual(rel["elementType"], "reference")
        self.assertEqual(rel["referenceTypeId"], "product")

    def test_enum_values_carried(self):
        keys = [v["key"] for v in _attr(self.pts["product"], "color")["values"]]
        self.assertEqual(keys, ["black", "white", "blue"])

    def test_structural_property_dropped(self):
        # childSKUs is the product->variant edge, not an attribute.
        self.assertIsNone(_attr(self.pts["product"], "childSKUs"))

    def test_custom_descriptor_flagged(self):
        self.assertIn("warrantyPlan", self.pts)
        decisions = self.pts["warrantyPlan"]["decisionsNeeded"]
        self.assertTrue(decisions)
        self.assertEqual(decisions[0]["recommendation"], "productType")

    def test_provenance_on_every_element(self):
        for pt in self.ccm["productTypes"]:
            self.assertEqual(pt["origin"], "source")
            self.assertIn("sourceRef", pt)
            for a in pt["attributes"]:
                self.assertEqual(a["origin"], "source")
                self.assertIn("confidence", a)


class SchemaConformanceTests(unittest.TestCase):
    def test_output_validates_against_ccm_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        ccm, _, _ = analyze(FIXTURE, client="Test Telco", domain="telecom")
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        jsonschema.validate(ccm, schema, cls=jsonschema.Draft202012Validator)


if __name__ == "__main__":
    unittest.main()

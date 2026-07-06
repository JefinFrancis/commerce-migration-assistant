"""Tests for the deterministic ATG database analyzer and reconciliation.

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

import db_extract  # noqa: E402
from analyze import analyze  # noqa: E402

FIXTURE_XML = os.path.join(ATG_DIR, "fixtures", "productCatalog.xml")
FIXTURE_SQL = os.path.join(ATG_DIR, "fixtures", "productCatalog_schema.sql")
SCHEMA = os.path.join(REPO_ROOT, "ccm", "schema", "ccm.schema.json")


def _attr(product_type, name):
    for a in product_type["attributes"]:
        if a["name"] == name:
            return a
    return None


class DdlParseTests(unittest.TestCase):
    def setUp(self):
        self.db = db_extract.parse_ddl(FIXTURE_SQL)
        self.tables = {t["name"]: t for t in self.db["tables"]}

    def test_all_tables_found(self):
        self.assertEqual(
            set(self.tables),
            {"dcs_product", "dcs_product_kw", "dcs_product_rel", "dcs_product_skus", "dcs_sku"},
        )

    def test_columns_and_nullability(self):
        cols = {c["name"]: c for c in self.tables["dcs_product"]["columns"]}
        self.assertFalse(cols["display_name"]["nullable"])
        self.assertFalse(cols["brand"]["nullable"])
        self.assertTrue(cols["launch_date"]["nullable"])

    def test_primary_key_detected(self):
        cols = {c["name"]: c for c in self.tables["dcs_product"]["columns"]}
        self.assertTrue(cols["product_id"]["primaryKey"])
        # composite PK on the multi table
        kw = {c["name"]: c for c in self.tables["dcs_product_kw"]["columns"]}
        self.assertTrue(kw["product_id"]["primaryKey"])
        self.assertTrue(kw["keyword"]["primaryKey"])

    def test_numeric_with_comma_param_not_split(self):
        cols = {c["name"]: c for c in self.tables["dcs_sku"]["columns"]}
        self.assertIn("list_price", cols)
        self.assertEqual(cols["list_price"]["sqlType"].replace(" ", ""), "NUMERIC(12,2)")

    def test_foreign_keys(self):
        fks = self.tables["dcs_product_skus"]["foreignKeys"]
        targets = {(fk["column"], fk["refTable"]) for fk in fks}
        self.assertIn(("product_id", "dcs_product"), targets)
        self.assertIn(("sku_id", "dcs_sku"), targets)


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.ccm, _, self.db = analyze(
            FIXTURE_XML, client="Test Telco", domain="telecom", db_path=FIXTURE_SQL
        )
        self.product = {pt["key"]: pt for pt in self.ccm["productTypes"]}["product"]

    def test_required_corrected_from_not_null(self):
        # brand is optional in the XML but NOT NULL in the DB -> required becomes True.
        self.assertTrue(_attr(self.product, "brand")["required"])

    def test_confidence_boosted_on_confirmed_column(self):
        # displayName (text, 0.95) confirmed by DB -> bumped.
        self.assertGreater(_attr(self.product, "displayName")["confidence"], 0.95)

    def test_db_only_column_surfaced(self):
        db_only = _attr(self.product, "internal_sku_code")
        self.assertIsNotNone(db_only)
        self.assertEqual(db_only["level"], "product")
        self.assertTrue(db_only["decisionsNeeded"])
        self.assertEqual(db_only["sourceRef"], "dcs_product.internal_sku_code")

    def test_no_spurious_db_only_for_consumed_columns(self):
        # keyword / related_id / sku columns are backed by XML props -> not duplicated.
        names = [a["name"] for a in self.product["attributes"]]
        self.assertEqual(names.count("keywords"), 1)
        self.assertNotIn("keyword", names)  # the raw column is not added separately
        self.assertNotIn("related_id", names)

    def test_pk_and_fk_columns_not_surfaced(self):
        names = [a["name"] for a in self.product["attributes"]]
        self.assertNotIn("product_id", names)
        self.assertNotIn("sku_id", names)

    def test_reconciled_output_validates_against_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        jsonschema.validate(self.ccm, schema, cls=jsonschema.Draft202012Validator)


if __name__ == "__main__":
    unittest.main()

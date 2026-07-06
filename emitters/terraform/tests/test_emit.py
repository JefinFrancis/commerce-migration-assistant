"""Tests for the Terraform emitter.

Validates generated HCL both structurally (content assertions) and syntactically
(parsing with python-hcl2 when available). Run from the repo root:
    python3 -m unittest discover -s emitters/terraform/tests
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EMIT_DIR = os.path.abspath(os.path.join(HERE, ".."))
REPO_ROOT = os.path.abspath(os.path.join(EMIT_DIR, "..", ".."))
sys.path.insert(0, EMIT_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "adapters", "atg"))

import emit  # noqa: E402
from analyze import analyze  # noqa: E402

EXAMPLE_CCM = os.path.join(REPO_ROOT, "ccm", "schema", "ccm.example.json")
FIXTURE_XML = os.path.join(REPO_ROOT, "adapters", "atg", "fixtures", "productCatalog.xml")
FIXTURE_SQL = os.path.join(REPO_ROOT, "adapters", "atg", "fixtures", "productCatalog_schema.sql")


def _hcl_valid(text):
    """Parse HCL with python-hcl2; return True/False, or None if lib unavailable."""
    try:
        import hcl2
    except ImportError:
        return None
    import io

    hcl2.load(io.StringIO(text))
    return True


class EmitFromExampleTests(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE_CCM, encoding="utf-8") as fh:
            self.ccm = json.load(fh)
        self.files = emit.emit(self.ccm)

    def test_versions_pins_provider(self):
        v = self.files["versions.tf"]
        self.assertIn('source  = "labd/commercetools"', v)
        self.assertIn("~> 1.20", v)

    def test_product_type_resource_and_levels(self):
        tf = self.files["product-types.tf"]
        self.assertIn('resource "commercetools_product_type" "device"', tf)
        self.assertIn('name  = "color"', tf)          # variant attribute
        self.assertIn('name  = "eco_rating"', tf)     # manual attribute

    def test_categories_use_for_each_with_parent_reference(self):
        tf = self.files["categories.tf"]
        self.assertIn("for_each = local.categories", tf)
        self.assertIn("commercetools_category.this[each.value.parent].id", tf)

    def test_customer_groups_for_each(self):
        tf = self.files["customer-groups.tf"]
        self.assertIn('resource "commercetools_customer_group" "this"', tf)
        self.assertIn("for_each = local.customer_groups", tf)

    def test_all_files_are_valid_hcl(self):
        checked = False
        for name, text in self.files.items():
            result = _hcl_valid(text)
            if result is None:
                self.skipTest("python-hcl2 not installed")
            self.assertTrue(result, "%s is not valid HCL" % name)
            checked = True
        self.assertTrue(checked)


class EmitFromAnalyzerOutputTests(unittest.TestCase):
    """End-to-end: ATG XML+DB -> CCM -> Terraform."""

    def setUp(self):
        self.ccm, _, _ = analyze(FIXTURE_XML, client="Test", domain="telecom", db_path=FIXTURE_SQL)
        self.files = emit.emit(self.ccm)

    def test_product_type_emitted_from_pipeline(self):
        tf = self.files["product-types.tf"]
        self.assertIn('resource "commercetools_product_type" "product"', tf)
        # enum attribute with its values
        self.assertIn('name = "enum"', tf)
        self.assertIn('key   = "black"', tf)
        # set of reference
        self.assertIn('name = "set"', tf)
        self.assertIn('reference_type_id = "product"', tf)
        # DB-only column carried through
        self.assertIn('name  = "internal_sku_code"', tf)

    def test_output_is_valid_hcl(self):
        result = _hcl_valid(self.files["product-types.tf"])
        if result is None:
            self.skipTest("python-hcl2 not installed")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()

"""Tests for the migration-report renderer.

Run from the repo root:
    python3 -m unittest discover -s reporters/tests
"""

import json
import os
import sys
import unittest
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTERS_DIR = os.path.abspath(os.path.join(HERE, ".."))
REPO_ROOT = os.path.abspath(os.path.join(REPORTERS_DIR, ".."))
sys.path.insert(0, REPORTERS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "adapters", "atg"))

import render  # noqa: E402
from analyze import analyze  # noqa: E402

EXAMPLE_CCM = os.path.join(REPO_ROOT, "ccm", "schema", "ccm.example.json")
FIXTURE_XML = os.path.join(REPO_ROOT, "adapters", "atg", "fixtures", "productCatalog.xml")
FIXTURE_SQL = os.path.join(REPO_ROOT, "adapters", "atg", "fixtures", "productCatalog_schema.sql")


class _WellFormed(HTMLParser):
    """Assert every non-void tag is balanced."""

    VOID = {"meta", "br", "hr", "img", "input", "link", "area", "base", "col", "source"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.ok = True

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass
        else:
            self.ok = False


def _assert_self_contained(test, html_text):
    test.assertTrue(html_text.lstrip().lower().startswith("<!doctype html>"))
    test.assertIn("</html>", html_text)
    test.assertIn("<style>", html_text)  # CSS inlined
    test.assertNotIn("<link", html_text)  # no external stylesheet
    test.assertNotIn('src="http', html_text)  # no external scripts/images
    p = _WellFormed()
    p.feed(html_text)
    test.assertTrue(p.ok and not p.stack, "HTML tags are not balanced")


class AnalysisReportTests(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE_CCM, encoding="utf-8") as fh:
            self.ccm = json.load(fh)
        self.html = render.render(self.ccm, "analysis")

    def test_self_contained_and_well_formed(self):
        _assert_self_contained(self, self.html)

    def test_shows_product_types_and_attributes(self):
        self.assertIn("commercetools_product_type" if False else "Device", self.html)
        self.assertIn("contract_term_months", self.html)

    def test_all_origin_badges_present(self):
        for origin in ("source", "domain-pack", "manual"):
            self.assertIn('class="badge %s"' % origin, self.html)

    def test_decisions_panel_present(self):
        self.assertIn("Decisions needed", self.html)
        self.assertIn("cost centers", self.html)  # from the example businessUnit decision

    def test_confidence_bar_rendered(self):
        self.assertIn('class="conf', self.html)
        self.assertIn('class="bar"', self.html)


class PlanReportTests(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE_CCM, encoding="utf-8") as fh:
            self.ccm = json.load(fh)
        self.html = render.render(self.ccm, "plan")

    def test_self_contained_and_well_formed(self):
        _assert_self_contained(self, self.html)

    def test_maps_ccm_to_terraform_resources(self):
        self.assertIn("commercetools_product_type", self.html)
        self.assertIn("commercetools_customer_group", self.html)
        self.assertIn("CCM → commercetools → Terraform", self.html)


class EndToEndReportTests(unittest.TestCase):
    def test_report_from_analyzer_output(self):
        ccm, _, _ = analyze(FIXTURE_XML, client="Test", domain="telecom", db_path=FIXTURE_SQL)
        html_text = render.render(ccm, "analysis")
        _assert_self_contained(self, html_text)
        # custom descriptor decision surfaced
        self.assertIn("warrantyPlan", html_text)
        self.assertIn("Decisions needed", html_text)
        # DB-only column present
        self.assertIn("internal_sku_code", html_text)


if __name__ == "__main__":
    unittest.main()

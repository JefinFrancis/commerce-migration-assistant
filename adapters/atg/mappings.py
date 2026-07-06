"""Deterministic ATG -> Canonical Commerce Model mapping rules.

These rules cover the mechanical majority of mappings (architecture doc §10).
Anything they cannot resolve confidently is returned with a `_decision` hint so
the caller can raise a `decisionsNeeded[]` entry for human/model review.
"""

import re

# ATG scalar data-type -> CCM attribute type.
SCALAR_MAP = {
    "string": "text",
    "big string": "text",
    "text": "text",
    "int": "number",
    "integer": "number",
    "long": "number",
    "short": "number",
    "byte": "number",
    "float": "number",
    "double": "number",
    "number": "number",
    "big decimal": "number",
    "boolean": "boolean",
    "date": "datetime",
    "timestamp": "datetime",
    "enumerated": "enum",
}

# Well-known standard ATG item-descriptors.
STANDARD_DESCRIPTORS = {
    "product", "sku", "category", "catalog", "folder", "price", "pricelist",
    "media", "media-external", "media-internal-binary", "media-internal-text",
}

# Structural relationship properties that describe the graph, not attributes.
STRUCTURAL_PROPERTIES = {
    "childskus", "parentcategory", "parentcategories", "ancestorcategories",
    "childproducts", "childcategories", "fixedchildproducts", "catalogs",
    "rootcatalog", "parentproducts",
}


def humanize(name):
    """camelCase / snake_case identifier -> "Title Case" label."""
    if not name:
        return name
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
    return " ".join(w.capitalize() for w in spaced.split())


def is_structural(prop):
    return (prop.get("name") or "").lower() in STRUCTURAL_PROPERTIES


def ccm_type_for(prop):
    """Map one raw property to (ccm_type, extra).

    `extra` may carry: values, elementType, referenceTypeId, _decision, _unknown.
    """
    data_type = prop["dataType"]

    # References (single or collection).
    target = prop.get("componentItemType") or prop.get("itemType")
    if target:
        if prop["multiValued"]:
            return "set", {"elementType": "reference", "referenceTypeId": target}
        return "reference", {"referenceTypeId": target}

    # Enumerations.
    if data_type == "enumerated":
        values = [
            {"key": o["value"], "label": {"en": o["value"]}}
            for o in prop["enumOptions"]
            if o.get("value")
        ]
        if prop["multiValued"]:
            return "set", {"elementType": "enum", "values": values}
        return "enum", {"values": values}

    # Scalar collections.
    if prop["multiValued"]:
        elem = SCALAR_MAP.get(prop.get("componentDataType") or "", "text")
        return "set", {"elementType": elem}

    # Map -> needs a modeling decision.
    if data_type == "map":
        return "text", {"_decision": "ATG 'map' property — model as a nested type or custom object"}

    # Known scalar.
    if data_type in SCALAR_MAP:
        return SCALAR_MAP[data_type], {}

    # Unknown -> low confidence + decision.
    return "text", {
        "_unknown": True,
        "_decision": f"Unknown ATG data-type '{data_type}' — confirm CCM attribute type",
    }


def confidence_for(ccm_type, extra):
    if extra.get("_unknown") or extra.get("_decision"):
        return 0.6
    if ccm_type in ("text", "number", "boolean", "datetime"):
        return 0.95
    if ccm_type == "enum":
        return 0.9
    return 0.8  # reference / set


# SQL column type -> CCM attribute type (base word, params stripped).
SQL_TYPE_PREFIX_MAP = [
    (("varchar", "char", "nvarchar", "nchar", "text", "clob", "longvarchar", "string"), "text"),
    (("int", "integer", "bigint", "smallint", "tinyint", "numeric", "decimal",
      "number", "float", "double", "real", "money"), "number"),
    (("timestamp", "datetime", "date", "time"), "datetime"),
    (("bit", "boolean", "bool"), "boolean"),
]


def sql_to_ccm_type(sql_type):
    base = re.split(r"[\s(]", (sql_type or "").strip().lower(), 1)[0]
    for prefixes, ccm_type in SQL_TYPE_PREFIX_MAP:
        if base in prefixes:
            return ccm_type
    return "text"


def classify_descriptor(name):
    """Return one of: 'product', 'sku', 'category', 'catalog', 'standard-other', 'custom'."""
    n = (name or "").lower()
    if n in ("product", "sku", "category", "catalog"):
        return n
    if n in STANDARD_DESCRIPTORS:
        return "standard-other"
    return "custom"

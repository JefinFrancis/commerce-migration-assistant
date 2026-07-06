"""Build Canonical Commerce Model fragments from an ATG raw inventory.

Applies the deterministic mapping rules and attaches provenance
(origin / sourceRef / confidence / decisionsNeeded) to every element.

When a database inventory is supplied, the codebase-derived model is reconciled
against it: `required` is corrected from NOT NULL, confidence is boosted on
confirmed columns, and DB-only columns (present in the schema but absent from the
repository XML) are surfaced as attributes carrying a decision.
"""

from mappings import (
    ccm_type_for,
    classify_descriptor,
    confidence_for,
    humanize,
    is_structural,
    sql_to_ccm_type,
)

# Columns that are infrastructure, not business attributes.
AUDIT_COLUMNS = {"version", "asset_version", "workspace_id", "branch_id", "is_head"}


def _db_column_index(db_inventory):
    index = {}
    for table in db_inventory["tables"]:
        for col in table["columns"]:
            index[(table["name"], col["name"])] = col
    return index


def _attribute(prop, level, source_file, db_index=None):
    ccm_type, extra = ccm_type_for(prop)
    attr = {
        "name": prop["name"],
        "label": {"en": humanize(prop["name"])},
        "type": ccm_type,
        "level": level,
        "required": bool(prop.get("required")),
        "origin": "source",
        "sourceRef": "%s:%s" % (source_file, prop.get("columnName") or prop["name"]),
        "confidence": confidence_for(ccm_type, extra),
    }
    if "values" in extra:
        attr["values"] = extra["values"]
    if "elementType" in extra:
        attr["elementType"] = extra["elementType"]
    if "referenceTypeId" in extra:
        attr["referenceTypeId"] = extra["referenceTypeId"]
    if extra.get("_decision"):
        attr["decisionsNeeded"] = [
            {"id": "D-attr-%s" % prop["name"], "question": extra["_decision"], "resolved": False}
        ]

    # Reconcile against the database column that backs this property.
    if db_index is not None:
        col = db_index.get((prop.get("table"), prop.get("columnName")))
        if col:
            if not col["nullable"]:
                attr["required"] = True
            attr["confidence"] = round(min(0.99, attr["confidence"] + 0.03), 2)
    return attr


def _db_only_attributes(descriptor, level, db_tables):
    """Columns present in the DB tables backing this descriptor but not in the XML."""
    if not db_tables:
        return []
    consumed = {(p.get("table"), p.get("columnName")) for p in descriptor["properties"]}
    out = []
    for table_name in descriptor.get("tables", []):
        table = db_tables.get(table_name)
        if not table:
            continue
        fk_cols = {fk["column"] for fk in table.get("foreignKeys", [])}
        for col in table["columns"]:
            if col.get("primaryKey") or col["name"] in fk_cols:
                continue
            if col["name"].lower() in AUDIT_COLUMNS:
                continue
            if (table_name, col["name"]) in consumed:
                continue
            out.append(
                {
                    "name": col["name"],
                    "label": {"en": humanize(col["name"])},
                    "type": sql_to_ccm_type(col["sqlType"]),
                    "level": level,
                    "required": not col["nullable"],
                    "origin": "source",
                    "sourceRef": "%s.%s" % (table_name, col["name"]),
                    "confidence": 0.65,
                    "decisionsNeeded": [
                        {
                            "id": "D-dbonly-%s" % col["name"],
                            "question": (
                                "Column %s.%s exists in the database but not in the "
                                "repository XML — confirm it maps to a CCM attribute."
                                % (table_name, col["name"])
                            ),
                            "resolved": False,
                        }
                    ],
                }
            )
    return out


def _attributes_from(descriptor, level, source_file, db_index=None, db_tables=None):
    attrs = []
    for prop in descriptor["properties"]:
        if is_structural(prop):
            continue  # relationship edges are not attributes
        attrs.append(_attribute(prop, level, source_file, db_index))
    attrs += _db_only_attributes(descriptor, level, db_tables)
    return attrs


def _custom_descriptor_entry(descriptor, source_file, db_index=None, db_tables=None):
    """A custom item-descriptor with no direct CT equivalent.

    Proposed as a product type (the common default) but carrying an explicit
    decision so a human confirms product type vs. custom Type vs. custom object.
    """
    name = descriptor["name"]
    return {
        "key": name,
        "name": {"en": descriptor.get("displayName") or humanize(name)},
        "origin": "source",
        "sourceRef": "%s#item-descriptor[name=%s]" % (source_file, name),
        "confidence": 0.5,
        "attributes": _attributes_from(descriptor, "product", source_file, db_index, db_tables),
        "decisionsNeeded": [
            {
                "id": "D-desc-%s" % name,
                "question": (
                    "Custom ATG item-descriptor '%s' has no direct commercetools "
                    "equivalent — realize as a product type, a Type (custom fields), "
                    "or a custom object?" % name
                ),
                "options": ["productType", "customFieldType", "customObject"],
                "recommendation": "productType",
                "resolved": False,
            }
        ],
    }


def build_ccm(inventory, meta, db_inventory=None):
    """Assemble a schema-valid CCM document from a raw ATG inventory.

    If `db_inventory` is provided, the model is reconciled against the database.
    """
    by_name = {d["name"]: d for d in inventory["itemDescriptors"]}
    source_file = inventory["sourceFile"]

    db_tables = {t["name"]: t for t in db_inventory["tables"]} if db_inventory else None
    db_index = _db_column_index(db_inventory) if db_inventory else None

    product_types = []

    # ATG convention: `product` (product-level) + `sku` (variant-level) -> one product type.
    if "product" in by_name or "sku" in by_name:
        attrs = []
        if "product" in by_name:
            attrs += _attributes_from(by_name["product"], "product", source_file, db_index, db_tables)
        if "sku" in by_name:
            attrs += _attributes_from(by_name["sku"], "variant", source_file, db_index, db_tables)
        product_types.append(
            {
                "key": "product",
                "name": {"en": "Product"},
                "origin": "source",
                "sourceRef": "%s#item-descriptor[name=product]" % source_file,
                "confidence": 0.9,
                "attributes": attrs,
            }
        )

    # Custom descriptors -> proposed product types carrying a decision.
    for descriptor in inventory["itemDescriptors"]:
        if classify_descriptor(descriptor["name"]) == "custom":
            product_types.append(
                _custom_descriptor_entry(descriptor, source_file, db_index, db_tables)
            )

    return {
        "meta": meta,
        "productTypes": product_types,
        # Category *instances* (the taxonomy tree) come from the database/website
        # analyzers, not the repository definition. Left empty by this analyzer.
        "categories": [],
    }

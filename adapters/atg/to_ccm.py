"""Build Canonical Commerce Model fragments from an ATG raw inventory.

Applies the deterministic mapping rules and attaches provenance
(origin / sourceRef / confidence / decisionsNeeded) to every element.
"""

from mappings import (
    ccm_type_for,
    classify_descriptor,
    confidence_for,
    humanize,
    is_structural,
)


def _attribute(prop, level, source_file):
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
            {
                "id": "D-attr-%s" % prop["name"],
                "question": extra["_decision"],
                "resolved": False,
            }
        ]
    return attr


def _attributes_from(descriptor, level, source_file):
    attrs = []
    for prop in descriptor["properties"]:
        if is_structural(prop):
            continue  # relationship edges are not attributes
        attrs.append(_attribute(prop, level, source_file))
    return attrs


def _custom_descriptor_entry(descriptor, source_file):
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
        "attributes": _attributes_from(descriptor, "product", source_file),
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


def build_ccm(inventory, meta):
    """Assemble a schema-valid CCM document from a raw ATG inventory."""
    by_name = {d["name"]: d for d in inventory["itemDescriptors"]}
    source_file = inventory["sourceFile"]

    product_types = []

    # ATG convention: `product` (product-level) + `sku` (variant-level) -> one product type.
    if "product" in by_name or "sku" in by_name:
        attrs = []
        if "product" in by_name:
            attrs += _attributes_from(by_name["product"], "product", source_file)
        if "sku" in by_name:
            attrs += _attributes_from(by_name["sku"], "variant", source_file)
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
            product_types.append(_custom_descriptor_entry(descriptor, source_file))

    return {
        "meta": meta,
        "productTypes": product_types,
        # Category *instances* (the taxonomy tree) come from the database/website
        # analyzers, not the repository definition. Left empty by this analyzer.
        "categories": [],
    }

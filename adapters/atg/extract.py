"""Deterministic extraction of ATG repository-definition XML.

Parses an ATG GSA repository-definition file into a raw inventory of
item-descriptors and their properties. NO model/LLM is involved — this is a
plain XML parser that scales to any repository size (architecture doc §10,
"Parse, don't read").
"""

import os
import xml.etree.ElementTree as ET

# ATG collection data-types -> the property is multi-valued.
COLLECTION_TYPES = {"list", "array", "set", "map"}


def _as_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def _parse_property(prop_el, multi_hint=False):
    """Turn a <property> element into a normalized dict."""
    data_type = (prop_el.get("data-type") or "string").strip().lower()
    enum_options = []
    for opt in prop_el.findall("option"):
        enum_options.append({"value": opt.get("value"), "code": opt.get("code")})
    if not enum_options:
        # Some definitions carry the value set as <attribute name="values" value="a,b,c"/>.
        for attr in prop_el.findall("attribute"):
            if attr.get("name") == "values" and attr.get("value"):
                enum_options = [
                    {"value": v.strip()} for v in attr.get("value").split(",") if v.strip()
                ]
    return {
        "name": prop_el.get("name"),
        "dataType": data_type,
        "columnName": prop_el.get("column-name"),
        "required": _as_bool(prop_el.get("required")),
        "multiValued": multi_hint or data_type in COLLECTION_TYPES,
        "componentItemType": prop_el.get("component-item-type"),
        "componentDataType": prop_el.get("component-data-type"),
        "itemType": prop_el.get("item-type"),
        "enumOptions": enum_options,
    }


def parse_repository(xml_path):
    """Parse a repository-definition file into a raw inventory dict.

    Returns: {"sourceFile": str, "itemDescriptors": [{name, superType, properties[]}]}
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    descriptors = []
    for it in root.iter("item-descriptor"):
        name = it.get("name")
        if not name:
            continue
        properties = []
        seen = set()

        def _add(prop, multi_hint=False):
            parsed = _parse_property(prop, multi_hint)
            if parsed["name"] and parsed["name"] not in seen:
                seen.add(parsed["name"])
                properties.append(parsed)

        # Properties usually live under <table> elements; a "multi" table implies
        # a multi-valued property.
        for table in it.iter("table"):
            multi = table.get("type", "") == "multi"
            for prop in table.findall("property"):
                _add(prop, multi_hint=multi)
        # Also accept properties declared directly under the item-descriptor.
        for prop in it.findall("property"):
            _add(prop)

        descriptors.append(
            {
                "name": name,
                "displayName": it.get("display-name"),
                "superType": it.get("super-type"),
                "properties": properties,
            }
        )

    return {"sourceFile": os.path.basename(xml_path), "itemDescriptors": descriptors}

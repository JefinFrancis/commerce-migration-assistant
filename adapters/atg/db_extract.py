"""Deterministic extraction of an ATG GSA database schema (SQL DDL).

Parses a CREATE TABLE / ALTER TABLE DDL dump into a raw inventory of tables,
columns (name, sqlType, nullable, primaryKey) and foreign keys. NO model
involved — a pragmatic SQL parser that scales to thousands of tables
(architecture doc §10).
"""

import os
import re


def _split_top_level(body):
    """Split a CREATE TABLE body on top-level commas (ignoring commas in parens)."""
    parts, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


_FK_RE = re.compile(
    r"foreign\s+key\s*\((\w+)\)\s*references\s+[`\"]?(\w+)[`\"]?\s*\((\w+)\)", re.I
)


def _parse_body(body):
    columns, foreign_keys, pk_cols = [], [], set()
    for raw in _split_top_level(body):
        line = raw.strip()
        if not line:
            continue
        low = line.lower()

        if low.startswith("primary key"):
            m = re.search(r"\((.*?)\)", line)
            if m:
                pk_cols |= {c.strip().strip('`"') for c in m.group(1).split(",")}
            continue
        if low.startswith(("foreign key", "constraint")):
            m = _FK_RE.search(line)
            if m:
                foreign_keys.append(
                    {"column": m.group(1), "refTable": m.group(2), "refColumn": m.group(3)}
                )
            m2 = re.search(r"primary\s+key\s*\((.*?)\)", line, re.I)
            if m2:
                pk_cols |= {c.strip().strip('`"') for c in m2.group(1).split(",")}
            continue
        if low.startswith(("unique", "key ", "index", "check")):
            continue

        m = re.match(r"[`\"]?(\w+)[`\"]?\s+(.+)", line)
        if not m:
            continue
        col_name, rest = m.group(1), m.group(2)
        nullable = not re.search(r"not\s+null", rest, re.I)
        is_pk = bool(re.search(r"primary\s+key", rest, re.I))
        type_match = re.match(r"([A-Za-z]+\s*(?:\([^)]*\))?)", rest)
        sql_type = type_match.group(1).strip() if type_match else rest.strip()
        columns.append(
            {"name": col_name, "sqlType": sql_type, "nullable": nullable, "primaryKey": is_pk}
        )
        if is_pk:
            pk_cols.add(col_name)
    return columns, foreign_keys, pk_cols


def parse_ddl(path):
    """Parse a DDL file into {"sourceFile": str, "tables": [...]}"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # Strip comments.
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

    tables, by_name = [], {}
    for m in re.finditer(r"create\s+table\s+[`\"]?(\w+)[`\"]?\s*\((.*?)\)\s*;", text, re.I | re.S):
        name, body = m.group(1), m.group(2)
        columns, foreign_keys, pk_cols = _parse_body(body)
        for col in columns:
            if col["name"] in pk_cols:
                col["primaryKey"] = True
        table = {"name": name, "columns": columns, "foreignKeys": foreign_keys}
        tables.append(table)
        by_name[name] = table

    # ALTER TABLE ... ADD [CONSTRAINT ...] FOREIGN KEY (...) REFERENCES ... (...)
    for m in re.finditer(
        r"alter\s+table\s+[`\"]?(\w+)[`\"]?\s+add\s+(?:constraint\s+\w+\s+)?"
        r"foreign\s+key\s*\((\w+)\)\s*references\s+[`\"]?(\w+)[`\"]?\s*\((\w+)\)",
        text,
        re.I,
    ):
        table = by_name.get(m.group(1))
        if table:
            table["foreignKeys"].append(
                {"column": m.group(2), "refTable": m.group(3), "refColumn": m.group(4)}
            )

    return {"sourceFile": os.path.basename(path), "tables": tables}

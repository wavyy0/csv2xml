#!/usr/bin/env python3

import argparse
import pandas as pd
import xml.etree.ElementTree as ET
from typing import List, Optional

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert semicolon-separated CSV to XML using dot-path headers.")
    p.add_argument("input", help="Path to input CSV (semicolon-separated).")
    p.add_argument("-o", "--output", default="output.xml", help="Path to output XML file (default: output.xml).")
    p.add_argument("--root-tag", default="root", help='Root XML tag name (container for all rows). Default: "root".')
    p.add_argument("--row-tag", default=None, help='Element name for each row. '
                                                   'If omitted and all headers share a first segment, that segment is used. '
                                                   'Otherwise defaults to "record".')
    p.add_argument("--encoding", default="utf-8", help="Output encoding. Default: utf-8.")
    p.add_argument("--keep-empty", action="store_true",
                   help="Include empty fields as empty XML elements (by default empty cells are skipped).")
    return p.parse_args()

def get_or_create(parent: ET.Element, tag: str) -> ET.Element:
    for child in parent:
        if child.tag == tag:
            return child
    new_child = ET.Element(tag)
    parent.append(new_child)
    return new_child

def set_nested_value(parent: ET.Element, path_segments: List[str], value: str) -> None:
    node = parent
    for i, seg in enumerate(path_segments):
        node = get_or_create(node, seg)
        if i == len(path_segments) - 1:
            node.text = value

def indent(elem: ET.Element, level: int = 0) -> None:
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():  # type: ignore[name-defined]
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def determine_row_tag(headers: List[str], explicit_row_tag: Optional[str]) -> str:
    if explicit_row_tag:
        return explicit_row_tag
    first_segments = {h.split(".")[0] for h in headers if "." in h}
    if len(first_segments) == 1:
        return next(iter(first_segments))
    return "record"

def main():
    args = parse_args()

    df = pd.read_csv(
        args.input,
        sep=";",
        dtype=str,
        keep_default_na=False,
        engine="python"
    )

    headers = list(df.columns)
    row_tag = determine_row_tag(headers, args.row_tag)

    def path_for_row(col_name: str) -> List[str]:
        parts = col_name.split(".")
        if len(parts) > 1 and parts[0] == row_tag:
            return parts[1:]
        return parts

    root = ET.Element(args.root_tag)

    for _, row in df.iterrows():
        row_elem = ET.SubElement(root, row_tag)

        for col in headers:
            val = row[col]

            if not args.keep_empty:
                if val is None:
                    continue
                if isinstance(val, float) and pd.isna(val):
                    continue
                if str(val).strip() == "":
                    continue

            text = "" if val is None else str(val)

            path_segments = path_for_row(col)
            set_nested_value(row_elem, path_segments, text)

    indent(root)
    tree = ET.ElementTree(root)
    tree.write(args.output, encoding=args.encoding, xml_declaration=True)

    print(f"Wrote XML to {args.output}")

if __name__ == "__main__":
    main()

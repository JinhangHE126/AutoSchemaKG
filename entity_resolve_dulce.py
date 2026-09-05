#!/usr/bin/env python3
"""
Minimal entity-resolution experiment on Dulce demo outputs.

Usage:
  python entity_resolve_dulce.py
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

BASE = Path("example/generated/dulce_demo")
NODE_CSV = BASE / "triples_csv" / "triple_nodes_Dulce_from_json_without_emb.csv"
EDGE_CSV = BASE / "triples_csv" / "triple_edges_Dulce_from_json_without_emb.csv"
OUT_DIR = BASE / "entity_resolved"

# Canonical name mapping for 4 main characters.
# Only merge high-confidence short aliases.
ALIAS = {
    # Alex
    "Agent Alex Mercer": "Alex Mercer",
    "Alex": "Alex Mercer",
    "Agent Mercer": "Alex Mercer",
    "Mercer": "Alex Mercer",
    # Sam
    "Sam": "Sam Rivera",
    # Jordan
    "Dr. Jordan Hayes": "Jordan Hayes",
    "Jordan": "Jordan Hayes",
    # Taylor
    "Taylor": "Taylor Cruz",
    "Agent Cruz": "Taylor Cruz",
}

# For reporting: which surface forms we care about.
VARIANT_GROUPS = {
    "Alex Mercer": [
        "Agent Alex Mercer",
        "Alex Mercer",
        "Alex",
        "Agent Mercer",
        "Mercer",
    ],
    "Sam Rivera": ["Sam Rivera", "Sam"],
    "Jordan Hayes": ["Dr. Jordan Hayes", "Jordan Hayes", "Jordan"],
    "Taylor Cruz": ["Taylor Cruz", "Taylor", "Agent Cruz"],
}

# Do NOT merge these even if similar.
BLOCKLIST_EXACT = {
    "Taylor Cruz's voice",
    "Taylor's steely gaze",
    "Agent Alex Mercer and Dr. Jordan Hayes",
}


def norm(name: str) -> str:
    if name in BLOCKLIST_EXACT:
        return name
    return ALIAS.get(name, name)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def count_entities(nodes: list[dict]) -> list[str]:
    return [
        r["name:ID"]
        for r in nodes
        if (r.get("type") or "").lower() == "entity"
    ]


def variant_stats(entity_names: set[str]) -> dict:
    stats = {}
    for canon, variants in VARIANT_GROUPS.items():
        present = [v for v in variants if v in entity_names]
        stats[canon] = {
            "variants_present": present,
            "num_variants": len(present),
        }
    return stats


def main() -> None:
    nodes = read_csv(NODE_CSV)
    edges = read_csv(EDGE_CSV)

    # ---------- BEFORE ----------
    before_entities = count_entities(nodes)
    before_entity_set = set(before_entities)
    before_variant = variant_stats(before_entity_set)
    before_edge_keys = {
        (e[":START_ID"], e.get("relation", ""), e[":END_ID"]) for e in edges
    }

    # ---------- RESOLVE NODES ----------
    # Keep first occurrence of each normalized name.
    resolved_nodes: dict[str, dict] = {}
    merge_log = defaultdict(set)  # canonical -> original names merged into it

    for row in nodes:
        old = row["name:ID"]
        new = norm(old)
        if new != old:
            merge_log[new].add(old)

        if new not in resolved_nodes:
            new_row = dict(row)
            new_row["name:ID"] = new
            resolved_nodes[new] = new_row
        else:
            # If an alias row is mapped onto an existing canonical row,
            # prefer keeping type/label from the existing one.
            pass

    # ---------- RESOLVE EDGES ----------
    resolved_edges = []
    seen_edges = set()
    dropped_self_loops = 0
    dropped_duplicate_edges = 0

    for row in edges:
        s = norm(row[":START_ID"])
        t = norm(row[":END_ID"])
        rel = row.get("relation", "")

        if s == t:
            dropped_self_loops += 1
            continue

        key = (s, rel, t)
        if key in seen_edges:
            dropped_duplicate_edges += 1
            continue
        seen_edges.add(key)

        new_row = dict(row)
        new_row[":START_ID"] = s
        new_row[":END_ID"] = t
        resolved_edges.append(new_row)

    # ---------- AFTER ----------
    after_nodes = list(resolved_nodes.values())
    after_entities = count_entities(after_nodes)
    after_entity_set = set(after_entities)
    after_variant = variant_stats(after_entity_set)

    metrics = {
        "before": {
            "num_nodes_total": len(nodes),
            "num_entity_nodes": len(before_entities),
            "num_edges": len(edges),
            "num_unique_edges": len(before_edge_keys),
            "variants": before_variant,
        },
        "after": {
            "num_nodes_total": len(after_nodes),
            "num_entity_nodes": len(after_entities),
            "num_edges": len(resolved_edges),
            "num_unique_edges": len(seen_edges),
            "variants": after_variant,
            "dropped_self_loops": dropped_self_loops,
            "dropped_duplicate_edges": dropped_duplicate_edges,
            "merged_into": {k: sorted(v) for k, v in merge_log.items()},
        },
    }

    # ---------- SAVE ----------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT_DIR / "nodes_resolved.csv",
        after_nodes,
        fieldnames=list(nodes[0].keys()),
    )
    write_csv(
        OUT_DIR / "edges_resolved.csv",
        resolved_edges,
        fieldnames=list(edges[0].keys()),
    )
    with open(OUT_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # Also save alias table for the note / email
    with open(OUT_DIR / "alias_table.json", "w", encoding="utf-8") as f:
        json.dump(
            {"alias": ALIAS, "blocklist": sorted(BLOCKLIST_EXACT)},
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ---------- PRINT SUMMARY ----------
    print("=== Entity Resolution Summary ===")
    print(f"Entity nodes: {metrics['before']['num_entity_nodes']} -> {metrics['after']['num_entity_nodes']}")
    print(f"Total nodes:  {metrics['before']['num_nodes_total']} -> {metrics['after']['num_nodes_total']}")
    print(f"Edges:        {metrics['before']['num_edges']} -> {metrics['after']['num_edges']}")
    print(f"Dropped self-loops: {dropped_self_loops}")
    print(f"Dropped duplicate edges: {dropped_duplicate_edges}")
    print()
    print("Variant counts (before -> after):")
    for canon in VARIANT_GROUPS:
        b = before_variant[canon]["num_variants"]
        a = after_variant[canon]["num_variants"]
        print(f"  {canon}: {b} -> {a}  before={before_variant[canon]['variants_present']}")
    print()
    print(f"Wrote: {OUT_DIR}/nodes_resolved.csv")
    print(f"Wrote: {OUT_DIR}/edges_resolved.csv")
    print(f"Wrote: {OUT_DIR}/metrics.json")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Build the shadcn registry output for the POPIA components.

Reads registry/registry.json, inlines each file's content and writes:
  registry/r/<item>.json      one registry item per file (registry-item schema)
  registry/r/registry.json    the index

Usage:
  python3 registry/build.py           build
  python3 registry/build.py --check   exit 1 if r/ is stale (for CI)

Python standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "registry.json"
OUT = HERE / "r"
ITEM_SCHEMA = "https://ui.shadcn.com/schema/registry-item.json"
REGISTRY_SCHEMA = "https://ui.shadcn.com/schema/registry.json"
ITEM_KEYS = (
    "name",
    "type",
    "title",
    "description",
    "dependencies",
    "devDependencies",
    "registryDependencies",
    "cssVars",
    "tailwind",
    "meta",
    "docs",
)


def dump(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def build_outputs() -> dict[str, str]:
    """Return {relative output path: file text} without touching disk."""
    registry = json.loads(SOURCE.read_text(encoding="utf-8"))
    if registry.get("$schema") != REGISTRY_SCHEMA:
        raise SystemExit(f"registry.json: $schema must be {REGISTRY_SCHEMA}")

    outputs: dict[str, str] = {}
    seen: set[str] = set()
    for item in registry.get("items", []):
        name = item.get("name")
        if not name or name in seen:
            raise SystemExit(f"registry.json: missing or duplicate item name {name!r}")
        seen.add(name)
        if not item.get("files"):
            raise SystemExit(f"{name}: no files")

        built: dict[str, object] = {"$schema": ITEM_SCHEMA}
        for key in ITEM_KEYS:
            if key in item:
                built[key] = item[key]

        files = []
        for f in item["files"]:
            src = HERE / f["path"]
            if not src.is_file():
                raise SystemExit(f"{name}: file not found {f['path']}")
            if f.get("type") == "registry:file" and not f.get("target"):
                raise SystemExit(f"{name}: registry:file entries need a target ({f['path']})")
            entry: dict[str, object] = {
                "path": f["path"],
                "content": src.read_text(encoding="utf-8"),
                "type": f["type"],
            }
            if f.get("target"):
                entry["target"] = f["target"]
            files.append(entry)
        built["files"] = files
        outputs[f"{name}.json"] = dump(built)

    index = {
        "$schema": REGISTRY_SCHEMA,
        "name": registry["name"],
        "homepage": registry["homepage"],
        "items": registry["items"],
    }
    outputs["registry.json"] = dump(index)
    return outputs


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit non-zero if r/ is out of date")
    args = parser.parse_args(argv)

    outputs = build_outputs()

    if args.check:
        stale: list[str] = []
        for rel, text in outputs.items():
            p = OUT / rel
            if not p.is_file() or p.read_text(encoding="utf-8") != text:
                stale.append(rel)
        extra = sorted(p.name for p in OUT.glob("*.json") if p.name not in outputs) if OUT.is_dir() else []
        if stale or extra:
            for s in stale:
                print(f"stale: r/{s}")
            for e in extra:
                print(f"extra: r/{e}")
            print("Run: python3 registry/build.py")
            return 1
        print(f"ok: r/ is up to date ({len(outputs)} files)")
        return 0

    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        if old.name not in outputs:
            old.unlink()
    for rel, text in outputs.items():
        (OUT / rel).write_text(text, encoding="utf-8")
    print(f"wrote {len(outputs)} files to {OUT.relative_to(HERE.parent)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

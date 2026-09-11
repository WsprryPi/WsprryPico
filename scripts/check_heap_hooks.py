#!/usr/bin/env python3
"""Audit direct calls in the linked pinned-newlib image; no hardware access.

This proves the checked direct call routing, not arbitrary function-pointer
provenance, allocator WCET, target memory sufficiency or RF acceptance.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess


ALLOCATORS = ("_malloc_r", "_calloc_r", "_realloc_r", "_free_r")


def validate(disassembly):
    edges = {}
    symbols = set()
    caller = None
    for line in disassembly.splitlines():
        label = re.fullmatch(r"[0-9a-f]+ <([^>]+)>:", line)
        if label:
            caller = label[1]
            symbols.add(caller)
            continue
        instruction = re.match(r"\s*[0-9a-f]+:\s+[0-9a-f ]+\t\s*(\S+)\s+(.*)", line)
        if not instruction or not caller:
            continue
        op, operands = instruction.groups()
        if not re.fullmatch(r"(?:blx?|b(?:eq|ne|cs|cc|mi|pl|vs|vc|hi|ls|ge|lt|gt|le)?)(?:\.[nw])?", op):
            continue
        target = re.search(r"<([^>]+)>", operands)
        if not target:
            if caller in ALLOCATORS and op in {"bl", "blx"}:
                raise ValueError("indirect allocator call needs review: " + caller)
            continue
        callee = target[1].split("+0x")[0]
        if caller != callee:
            edges.setdefault(callee, set()).add(caller)
    for allocator in ALLOCATORS:
        wrapper = "__wrap_" + allocator
        if allocator not in symbols or wrapper not in symbols:
            raise ValueError("missing allocator/wrapper: " + allocator)
        if edges.get(allocator) != {wrapper}:
            raise ValueError("allocator bypass or missing call: " + allocator)
        if not edges.get(wrapper):
            raise ValueError("unused wrapper: " + wrapper)
    # The pinned realloc implementation allocates before freeing when it moves
    # a block. Nested entry observations must exist to see that transient peak.
    for wrapper in ("__wrap__malloc_r", "__wrap__free_r"):
        if "_realloc_r" not in edges[wrapper]:
            raise ValueError("missing nested realloc observation: " + wrapper)
    if "_calloc_r" not in edges["__wrap__malloc_r"]:
        raise ValueError("missing nested calloc observation")
    if "__smakebuf_r" not in edges["__wrap__malloc_r"]:
        raise ValueError("missing direct stdio allocation coverage")
    for internal, owners in {"_mallinfo_r": {"mallinfo"},
                             "__malloc_update_mallinfo": {"_mallinfo_r"},
                             "_malloc_trim_r": {"_free_r"}}.items():
        if internal in symbols and edges.get(internal) != owners:
            raise ValueError("internal allocator bypass: " + internal)
    permitted = {"__wrap_mallinfo", "sample", "leave", "wsprry_heap_snapshot",
                 *("__wrap_" + a for a in ALLOCATORS)}
    if not edges.get("mallinfo") or not edges["mallinfo"] <= permitted:
        raise ValueError("unserialized mallinfo or changed observation code")
    return {name: sorted(edges.get(name, ())) for name in
            (*ALLOCATORS, *("__wrap_" + a for a in ALLOCATORS), "mallinfo")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    args = parser.parse_args()
    disassembly = subprocess.check_output(
        ["arm-none-eabi-objdump", "-d", str(args.elf)], text=True)
    print(json.dumps(validate(disassembly), sort_keys=True))


if __name__ == "__main__":
    main()

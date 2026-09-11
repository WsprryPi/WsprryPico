#!/usr/bin/env python3
"""Mutation tests for allocator routing admission, without an SDK or device."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "checker", Path(__file__).resolve().parents[1] / "scripts/check_heap_hooks.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def fixture():
    edges = {
        "__wrap__malloc_r": ["_malloc_r"],
        "__wrap__calloc_r": ["_calloc_r"],
        "__wrap__realloc_r": ["_realloc_r"],
        "__wrap__free_r": ["_free_r"],
        "malloc": ["__wrap__malloc_r"],
        "calloc": ["__wrap__calloc_r"],
        "realloc": ["__wrap__realloc_r"],
        "free": ["__wrap__free_r"],
        "_malloc_r": [], "_free_r": [],
        "_calloc_r": ["__wrap__malloc_r"],
        "_realloc_r": ["__wrap__malloc_r", "__wrap__free_r"],
        "__smakebuf_r": ["__wrap__malloc_r"],
        "__wrap_mallinfo": ["mallinfo"],
    }
    return "\n".join("10000000 <" + caller + ">:\n" + "\n".join(
        "10000000: f000 f800\tbl\t10000004 <" + target + ">" for target in targets)
        for caller, targets in edges.items())


class RoutingTests(unittest.TestCase):
    def test_direct_coverage(self):
        self.assertEqual(checker.validate(fixture())["_malloc_r"], ["__wrap__malloc_r"])

    def test_reject_bypass(self):
        with self.assertRaises(ValueError):
            checker.validate(fixture() + "\n10000000 <foreign>:\n10000000: f000 f800\tbl\t10000004 <_malloc_r>")

    def test_conditional_bypass(self):
        with self.assertRaises(ValueError):
            checker.validate(fixture() + "\n10000000 <foreign>:\n10000000: f000 f800\tbne.w\t10000004 <_malloc_r>")

    def test_missing_transient_or_stdio(self):
        for name in ("_realloc_r", "_calloc_r", "__smakebuf_r", "__wrap__malloc_r"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checker.validate(fixture().replace("<" + name + ">:", "<missing>:"))

    def test_indirect_allocator(self):
        with self.assertRaises(ValueError):
            checker.validate(fixture().replace("10000000 <_malloc_r>:",
                "10000000 <_malloc_r>:\n10000000: 4798\tblx\tr3"))

    def test_mallinfo_bypass(self):
        with self.assertRaises(ValueError):
            checker.validate(fixture().replace("<__wrap_mallinfo>:", "<foreign>:"))


if __name__ == "__main__":
    unittest.main()

"""Reject ELF/UF2 content substitution and out-of-application load segments."""
import copy
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from firmware_payload import verify_payload


def images():
    payload = b'identical application payload\0'
    elf = bytearray(84 + len(payload))
    elf[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H', elf, 18, 40)
    struct.pack_into('<I', elf, 28, 52)
    struct.pack_into('<HH', elf, 42, 32, 1)
    struct.pack_into('<8I', elf, 52, 1, 84, 0x10000000, 0x10000000,
                     len(payload), len(payload), 5, 4)
    elf[84:] = payload
    uf2 = bytearray(1024)
    struct.pack_into('<8I', uf2, 0, 0x0a324655, 0x9e5d5157, 0x2000,
                     0x10000000, 256, 0, 1, 0xe48bff59)
    uf2[32:32 + len(payload)] = payload
    struct.pack_into('<I', uf2, 512 + 12, 0x10ffff00)
    return elf, uf2


class PayloadTests(unittest.TestCase):
    def test_exact_load_payload_and_declared_application_boundary(self):
        elf, uf2 = images()
        verify_payload(elf, uf2)
        with self.assertRaisesRegex(ValueError, 'outside application'):
            verify_payload(elf, uf2, application_end=0x10000010)

    def test_changed_payload_and_extra_nonpadding_bytes_are_rejected(self):
        elf, uf2 = images()
        changed = copy.copy(uf2)
        changed[32] ^= 1
        with self.assertRaisesRegex(ValueError, 'differs from ELF'):
            verify_payload(elf, changed)
        changed = copy.copy(uf2)
        changed[287] = 42
        with self.assertRaisesRegex(ValueError, 'outside ELF'):
            verify_payload(elf, changed)

    def test_wrong_architecture_missing_e10_and_header_overrun_are_rejected(self):
        elf, uf2 = images()
        for position, value in ((18, 1), (28, 255), (44, 65)):
            changed = copy.copy(elf)
            changed[position] = value
            with self.subTest(position=position), self.assertRaises(ValueError):
                verify_payload(changed, uf2)
        changed = copy.copy(uf2)
        struct.pack_into('<I', changed, 512 + 12, 0x10000100)
        with self.assertRaises(ValueError):
            verify_payload(elf, changed)


if __name__ == '__main__':
    unittest.main()

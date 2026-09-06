import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_standalone_image import validate_uf2


def block(address, workaround=False):
    data = bytearray(512)
    struct.pack_into('<8I', data, 0, 0x0A324655, 0x9E5D5157,
                     0xA000 if workaround else 0x2000, address, 256, 0, 2,
                     0xE48BFF57 if workaround else 0xE48BFF59)
    struct.pack_into('<I', data, 508, 0x0AB16F30)
    if workaround:
        data[32:288] = bytes([0xEF]) * 256
        struct.pack_into('<I', data, 288, 0x9957E304)
    return data


class ImageTests(unittest.TestCase):
    def test_separate_application_journal_and_boot_regions(self):
        validate_uf2(block(0x103FAF00) + block(0x10FFFF00, True))
        # Reject ordinary writes and a relocated boot block in the journals.
        for address in (0x103FB000, 0x103FC000, 0x103FEF00, 0x103FFF00):
            for workaround in (False, True):
                with self.assertRaises(ValueError):
                    validate_uf2(block(address, workaround))
        bad = block(0x10FFFF00, True)
        bad[32] ^= 1
        with self.assertRaises(ValueError):
            validate_uf2(bad)
        for malformed in (b'', bytes(512), block(0x10000000)[:-1]):
            with self.assertRaises(ValueError):
                validate_uf2(malformed)


if __name__ == '__main__':
    unittest.main()

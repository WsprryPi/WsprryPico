#!/usr/bin/env python3
"""Read-only linked flash reservation and UF2 payload-boundary check."""
import pathlib
import re
import struct
import subprocess
import sys


def validate_uf2(uf2):
    if not uf2 or len(uf2) % 512:
        raise ValueError("Invalid UF2 block length")
    for offset in range(0, len(uf2), 512):
        magic0, magic1, flags, address, size = struct.unpack_from("<5I", uf2, offset)
        if ((magic0, magic1) != (0x0A324655, 0x9E5D5157) or
                struct.unpack_from("<I", uf2, offset + 508)[0] != 0x0AB16F30 or
                not 0 < size <= 476):
            raise ValueError("Invalid UF2 header")
        # Pinned picotool emits the RP2350-E10 absolute-family block. Its
        # payload can occupy the final physical page, outside both journals.
        family = struct.unpack_from("<I", uf2, offset + 28)[0]
        workaround = (address == 0x10FFFF00 and flags == 0xA000 and
                      family == 0xE48BFF57 and size == 256 and
                      uf2[offset + 32:offset + 288] == bytes([0xEF]) * 256 and
                      struct.unpack_from("<I", uf2, offset + 288)[0] == 0x9957E304)
        if not workaround and not flags & 1 and not (0x10000000 <= address < address + size <= 0x103FB000):
            raise ValueError("UF2 payload outside reserved application region")


def main():
    elf = pathlib.Path(sys.argv[1])
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("check_endpoint_image.py")),
                    str(elf)], check=True)
    map_text = pathlib.Path(str(elf) + ".map").read_text()
    if not re.search(r"^FLASH\s+0x10000000\s+0x003fb000\s+xr$", map_text, re.MULTILINE):
        raise SystemExit("Missing last-20-KiB flash reservation")
    try:
        validate_uf2(elf.with_suffix(".uf2").read_bytes())
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print("Linked FLASH ends at 0x103fb000; journals end below the reserved boot sector")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Read-only linked flash reservation and UF2 payload-boundary check."""
import pathlib
import re
import struct
import subprocess
import sys

elf = pathlib.Path(sys.argv[1])
subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("check_endpoint_image.py")),
                str(elf)], check=True)
map_text = pathlib.Path(str(elf) + ".map").read_text()
match = re.search(r"^FLASH\s+0x10000000\s+0x003fc000\s+xr$", map_text, re.MULTILINE)
if not match:
    raise SystemExit("Missing last-16-KiB flash reservation")
uf2 = elf.with_suffix(".uf2").read_bytes()
if len(uf2) % 512:
    raise SystemExit("Invalid UF2 block length")
for offset in range(0, len(uf2), 512):
    magic0, magic1, flags, address, size = struct.unpack_from("<5I", uf2, offset)
    if (magic0, magic1) != (0x0A324655, 0x9E5D5157):
        raise SystemExit("Invalid UF2 header")
    # Pinned picotool emits the RP2350-E10 absolute-family ignore block.
    # It carries an explicit RP2 ignore extension, not writable payload.
    family = struct.unpack_from("<I", uf2, offset + 28)[0]
    ignored = (flags == 0xA000 and family == 0xE48BFF57 and size == 256
               and uf2[offset + 32:offset + 288] == bytes([0xEF]) * 256
               and struct.unpack_from("<I", uf2, offset + 288)[0] == 0x9957E304)
    if not ignored and not flags & 1 and not (0x10000000 <= address < address + size <= 0x103FC000):
        raise SystemExit("UF2 payload outside reserved application region")
print("Linked FLASH ends at 0x103fc000; UF2 leaves the final 16 KiB untouched")

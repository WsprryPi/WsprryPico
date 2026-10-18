"""Compare ARM ELF load segments with the exact RP2350 UF2 payload."""
import struct

def require(ok, message):
    if not ok:
        raise ValueError(message)

def verify_payload(elf, uf2, application_end=0x103f3000):
    require(len(elf) >= 52 and elf[:7] == b'\x7fELF\x01\x01\x01' and
            struct.unpack_from('<H', elf, 18)[0] == 40, 'ARM little-endian ELF32 required')
    offset = struct.unpack_from('<I', elf, 28)[0]
    stride, count = struct.unpack_from('<HH', elf, 42)
    require(stride == 32 and 0 < count <= 64 and offset + stride*count <= len(elf),
            'bounded ELF program headers')
    pages = {}
    e10_blocks = 0
    for i in range(0, len(uf2), 512):
        flags, address, size = struct.unpack_from('<III', uf2, i+8)
        if address == 0x10ffff00:
            e10_blocks += 1
            require(e10_blocks <= 1, 'duplicate E10 block')
            continue # exact E10 contents already checked by validate_uf2
        number, total, family = struct.unpack_from('<III', uf2, i+20)
        require(flags == 0x2000 and family == 0xe48bff59 and number == len(pages) and
                total == (len(uf2)//512)-1 and size == 256 and address % 256 == 0,
                'ordinary UF2 flash page required')
        require(address not in pages, 'duplicate UF2 page')
        pages[address] = uf2[i+32:i+32+size]
    covered = set()
    for i in range(count):
        kind, file_offset, _, address, size, _, _, _ = struct.unpack_from('<8I', elf, offset+i*stride)
        if kind != 1 or size == 0:
            continue
        require(0x10000000 <= address < address+size <= application_end and
                file_offset+size <= len(elf), 'ELF load segment outside application')
        for n in range(size):
            page = (address+n) & ~255
            require(page in pages and pages[page][(address+n) & 255] == elf[file_offset+n],
                    'UF2 payload differs from ELF')
            covered.add(address+n)
    require(e10_blocks == 1 and covered, 'E10 or ELF load payload absent')
    for address, payload in pages.items():
        require(all(address+i in covered or b in (0, 255) for i,b in enumerate(payload)),
                'unexpected UF2 payload outside ELF segments')

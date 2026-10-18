"""Offline PCAP, radiotap and 802.11 frame decoding; no host or device access."""
import struct

def radio_frames(path, live=False):
    data = path.read_bytes()
    if len(data) < 24 or data[:4] != b'\xd4\xc3\xb2\xa1':
        raise ValueError('Incomplete or unsupported monitor PCAP')
    if struct.unpack_from('<HH', data, 4) != (2, 4):
        raise ValueError('Unsupported PCAP version')
    if struct.unpack_from('<I', data, 20)[0] != 127:
        raise ValueError('Monitor capture is not radiotap')
    frames = []
    offset = 24
    while offset + 16 <= len(data):
        sec, us, size, original = struct.unpack_from('<IIII', data, offset)
        if us >= 1_000_000:
            raise ValueError('Invalid PCAP microseconds')
        if offset + 16 + size > len(data):
            if live:
                break  # Live writer may not have completed the last record yet.
            raise ValueError('Incomplete monitor record')
        if size != original:
            raise ValueError('Truncated monitor frame')
        wire = data[offset + 16:offset + 16 + size]
        offset += 16 + size
        if len(wire) < 8 or wire[0] != 0:
            continue
        rt = struct.unpack_from('<H', wire, 2)[0]
        if rt < 8 or rt + 10 > len(wire):
            continue
        present = struct.unpack_from('<I', wire, 4)[0]
        fields = 8
        bitmap = present
        while bitmap & 0x80000000:
            if fields + 4 > rt:
                raise ValueError('Incomplete radiotap presence bitmap')
            bitmap = struct.unpack_from('<I', wire, fields)[0]
            fields += 4
        if present & 1:  # TSFT precedes Flags and is aligned to eight bytes.
            fields = (fields + 7) // 8 * 8 + 8
        if present & 2:
            if fields >= rt:
                raise ValueError('Missing radiotap Flags field')
            if wire[fields] & 0x40:  # Receiver explicitly marked a bad FCS.
                continue
        w = wire[rt:]
        fc = struct.unpack_from('<H', w)[0]
        kind, subtype = (fc >> 2) & 3, (fc >> 4) & 15
        if fc & 3 or kind == 3 or (kind != 1 and len(w) < 24):
            continue
        addresses = [w[4:10].hex(':')]
        if len(w) >= 16:
            addresses.append(w[10:16].hex(':'))
        if kind != 1 and len(w) >= 24:
            addresses.append(w[16:22].hex(':'))
        frame = {'epoch_ns': sec * 10**9 + us * 1000,
                       'type': kind, 'subtype': subtype, 'retry': bool(fc & 0x800),
                       'protected': bool(fc & 0x4000), 'addresses': addresses,
                       'bytes': len(w)}
        if kind == 0 and not frame['protected']:
            if subtype == 11 and len(w) >= 30:
                frame['authentication'] = dict(zip(('algorithm', 'transaction', 'status'),
                                                     struct.unpack_from('<HHH', w, 24)))
            if subtype in (1, 3) and len(w) >= 30:
                frame['association_status'] = struct.unpack_from('<H', w, 26)[0]
        frames.append(frame)
    if not live and offset != len(data):
        raise ValueError('Incomplete monitor record header')
    return frames

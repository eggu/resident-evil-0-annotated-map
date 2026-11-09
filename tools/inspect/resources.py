"""Read-only readers for the RE0 ARC v7 and GUI 0x22013 resources.

Layout evidence: verification/discovery.md. Unknown GUI values remain typed records.
"""
from dataclasses import dataclass
import hashlib
import struct
import zlib


def unpack(data, fmt, offset):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ValueError(f'truncated structure at {offset:#x}')
    return struct.unpack_from(fmt, data, offset)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Member:
    name: str
    kind: int
    compressed_size: int
    size: int
    flags: int
    offset: int


class Arc:
    def __init__(self, data):
        self.data = data
        magic, version, count = unpack(data, '<4sHH', 0)
        if magic != b'ARC\0' or version != 7:
            raise ValueError('expected ARC version 7')
        end = 8 + count * 80
        if end > len(data):
            raise ValueError('truncated ARC directory')
        self.members = []
        seen = set()
        for i in range(count):
            at = 8 + i * 80
            rawname, kind, compressed, rawsize, offset = unpack(data, '<64s4I', at)
            if b'\0' not in rawname:
                raise ValueError('unterminated ARC member name')
            name = rawname.split(b'\0', 1)[0].decode('ascii')
            # Names identify resources, never filesystem destinations.
            if not name or (name, kind) in seen:
                raise ValueError('empty or duplicate ARC member identity')
            seen.add((name, kind))
            if offset < end or offset + compressed > len(data):
                raise ValueError('ARC member outside payload area')
            self.members.append(Member(name, kind, compressed, rawsize & 0x1fffffff,
                                       rawsize >> 29, offset))

    def read(self, member, limit=64 * 1024 * 1024):
        if member not in self.members:
            raise ValueError('member does not belong to archive')
        if member.size > limit:
            raise ValueError('ARC member exceeds decompression limit')
        payload = self.data[member.offset:member.offset + member.compressed_size]
        dec = zlib.decompressobj()
        try:
            result = dec.decompress(payload, member.size + 1)
        except zlib.error as e:
            raise ValueError('invalid compressed ARC member') from e
        if len(result) != member.size or not dec.eof or dec.unused_data or dec.unconsumed_tail:
            raise ValueError('ARC decompressed size or stream boundary mismatch')
        return result


def mloc(data):
    magic, version, count = unpack(data, '<4sIB', 0)
    if magic != b'mloc' or version != 1 or len(data) != 9 + count:
        raise ValueError('invalid mloc v1 record')
    return list(data[9:])  # Meaning of each byte is not assumed to be a floor ID.


def texture_info(data):
    magic, version, dimensions, format_word, offset = unpack(data, '<4s4I', 0)
    if magic != b'TEX\0' or version != 0x2000209d:
        raise ValueError('unsupported TEX header')
    width, height = (dimensions >> 6) & 8191, (dimensions >> 19) & 8191
    mips, faces = dimensions & 63, format_word & 255
    if not width or not height or not mips or faces != 1 or not 20 <= offset < len(data):
        raise ValueError('invalid or unsupported TEX dimensions/payload')
    return dict(width=width, height=height, mips=mips, faces=faces,
                format=(format_word >> 8) & 255, offset=offset)


class Gui:
    """Static object/instance properties only; animation evaluation is not implemented."""
    def __init__(self, data):
        self.data = data
        magic, version, size = unpack(data, '<4sII', 0)
        if magic != b'GUI\0' or version != 0x22013 or size != len(data) or len(data) < 0x130:
            raise ValueError('unsupported or truncated GUI')
        self.strings = self.u32(0x104)
        if not 0x130 <= self.strings < len(data):
            raise ValueError('GUI string pool outside file')
        self.objects = self.records(self.u32(0xac), self.u32(0x30), False)
        self.instances = self.records(self.u32(0xbc), self.u32(0x44), True)
        self.width, self.height = self.u32(0x98), self.u32(0x9c)
        self.animations = {}
        for i in range(self.u32(0x28)):
            row = unpack(data, '<6I', self.u32(0xa4) + i * 24)
            if row[0] in self.animations or row[3] >= len(self.objects):
                raise ValueError('invalid GUI animation identity/root')
            self.animations[row[0]] = dict(id=row[0], root=row[3], raw=list(row))
        self.textures = {}
        for i in range(self.u32(0x70)):
            row = unpack(data, '<16I', self.u32(0xe8) + i * 64)
            if row[0] in self.textures:
                raise ValueError('duplicate GUI texture ID')
            self.textures[row[0]] = dict(id=row[0], path=self.string(row[11]),
                                        name=self.string(row[12]))

    def u32(self, offset):
        return unpack(self.data, '<I', offset)[0]

    def string(self, index):
        start = self.strings + index
        if not self.strings <= start < len(self.data):
            raise ValueError('GUI string reference outside pool')
        end = self.data.find(b'\0', start)
        if end < 0:
            raise ValueError('unterminated GUI string')
        return self.data[start:end].decode('utf-8')

    def property(self, index):
        if not 0 <= index < self.u32(0x38):
            raise ValueError('GUI property index outside table')
        at = self.u32(0xb4) + index * 16
        kind, reserved, name, value = unpack(self.data, '<4I', at)
        if reserved:
            raise ValueError('unsupported GUI property reserved word')
        if kind >> 8:
            return self.string(name), {'unresolved_type': kind, 'raw': value}
        if kind in (1, 2, 7, 8, 9, 10, 11, 12, 13, 14, 16, 19):
            at = self.u32(0x110) + value
            decoded = unpack(self.data, '<f' if kind == 2 else '<i', at)[0]
        elif kind == 3:
            decoded = unpack(self.data, '<B', self.u32(0x10c) + value)[0]
            if decoded not in (0, 1):
                raise ValueError('invalid GUI boolean')
            decoded = bool(decoded)
        elif kind == 4:
            decoded = list(unpack(self.data, '<4f', self.u32(0x114) + value))
        elif kind in (17, 18):
            decoded = value
        else:
            decoded = {'unresolved_type': kind, 'raw': value}
        return self.string(name), decoded

    def records(self, start, count, instance):
        if start < 0x130 or count > len(self.data) // 36 or start + count * 36 > len(self.data):
            raise ValueError('GUI record table outside file')
        records = []
        for i in range(count):
            v = unpack(self.data, '<9I', start + i * 36)
            name, propcount, propstart = (v[5], v[4], v[7]) if instance else (v[4], v[1] & 255, v[6])
            if propstart + propcount > self.u32(0x38):
                raise ValueError('GUI property range outside table')
            props = {}
            for j in range(propstart, propstart + propcount):
                key, value = self.property(j)
                if key in props:
                    raise ValueError('duplicate GUI property')
                props[key] = value
            records.append(dict(index=i, name=self.string(name), raw=list(v), properties=props))
        return records


def resource_kind(name):
    return (~zlib.crc32(name.encode('ascii'))) & 0x7fffffff


def event_script_index(data):
    """rEventScript index from 0x57d100; group tags/extra words stay uninterpreted."""
    count, *reserved = unpack(data, '>4I', 0)
    end = 16 + count * 16
    if count > 32 or end > len(data):
        raise ValueError('unsupported or truncated event-script group table')
    records = [unpack(data, '>4I', 16+i*16) for i in range(count)]
    for tag, offset, extra0, extra1 in records:
        if offset and not end <= offset <= len(data):
            raise ValueError('event-script payload reference outside body')
    boundaries = sorted({r[1] for r in records if r[1]} | {len(data)})
    groups = []
    for i, row in enumerate(records):
        tag, offset, extra0, extra1 = row
        length = next((stop-offset for stop in boundaries if stop>offset),0) if offset else None
        groups.append(dict(index=i, tag=tag, offset=offset, extra_words=[extra0,extra1],
                           payload_extent=length,
                           payload_sha256=sha256(data[offset:offset+length]) if offset else None,
                           interpretation='unresolved'))
    return dict(reserved_words=reserved, groups=groups)

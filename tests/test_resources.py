import io
from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/inspect'))
sys.path.insert(0, str(ROOT/'emulator'))
from resources import Arc, Gui, mloc, texture_info, event_script_index, resource_kind
from render import descendants, decode_texture


def archive(payload=b'example', *, name=b'room\\test', rawsize=None):
    compressed = zlib.compress(payload)
    return (b'ARC\0'+struct.pack('<HH',7,1)
            +struct.pack('<64s4I',name,0x44c8ac26,len(compressed),len(payload) if rawsize is None else rawsize,88)
            +compressed)


def gui_fixture():
    """Tiny synthetic GUI; includes packed count flags and separate scalar/vector pools."""
    b = bytearray(0x400)
    struct.pack_into('<4sII',b,0,b'GUI\0',0x22013,len(b))
    for o,v in {0x30:1,0x38:2,0x44:1,0x98:1280,0x9c:720,
                0xac:0x130,0xb4:0x180,0xbc:0x1c0,0x104:0x300,
                0x10c:0x240,0x110:0x250,0x114:0x280}.items():
        struct.pack_into('<I',b,o,v)
    struct.pack_into('<9I',b,0x130,1,0x102,0xffffffff,0xffffffff,0,0,0,0,0xffffffff)
    struct.pack_into('<9I',b,0x1c0,2,0,0xffffffff,0xffffffff,2,0,0,0,0xffffffff)
    strings=b'root\0PosX\0Size\0'
    b[0x300:0x300+len(strings)]=strings
    struct.pack_into('<4I',b,0x180,2,0,5,0)
    struct.pack_into('<4I',b,0x190,4,0,10,0)
    struct.pack_into('<f',b,0x250,-12.5)
    struct.pack_into('<4f',b,0x280,16,8,0,0)
    return b


class ResourcesTest(unittest.TestCase):
    def test_resource_class_hashes_match_known_archive_kinds(self):
        self.assertEqual(resource_kind('rTexture'),0x241f5deb)
        self.assertEqual(resource_kind('rGUI'),0x22948394)
        self.assertEqual(resource_kind('rEventScript'),0x714ec77c)

    def test_event_groups_keep_zero_offset_unresolved(self):
        data=struct.pack('>12I',2,0,0,0,18,48,7,8,31,0,9,10)+b'body'
        parsed=event_script_index(data)
        self.assertEqual(parsed['groups'][0]['payload_extent'],4)
        self.assertEqual(parsed['groups'][0]['extra_words'],[7,8])
        self.assertIsNone(parsed['groups'][1]['payload_extent'])
        self.assertEqual(parsed['groups'][1]['interpretation'],'unresolved')

    def test_event_groups_reject_truncation_and_header_offsets(self):
        for data in [bytes(4),struct.pack('>4I',33,0,0,0),struct.pack('>8I',1,0,0,0,6,8,0,0)]:
            with self.subTest(data=data),self.assertRaises(ValueError):event_script_index(data)

    def test_arc_round_trip_and_flags(self):
        a=Arc(archive(rawsize=0x40000007))
        self.assertEqual(a.read(a.members[0]),b'example')
        self.assertEqual(a.members[0].flags,2)

    def test_arc_truncated_table(self):
        with self.assertRaises(ValueError):Arc(archive()[:40])

    def test_arc_payload_overlaps_directory(self):
        b=bytearray(archive());struct.pack_into('<I',b,84,8)
        with self.assertRaises(ValueError):Arc(b)

    def test_arc_rejects_decompression_size_mismatch(self):
        a=Arc(archive(rawsize=6))
        with self.assertRaises(ValueError):a.read(a.members[0])

    def test_arc_decompression_limit(self):
        a=Arc(archive())
        with self.assertRaises(ValueError):a.read(a.members[0],limit=3)

    def test_arc_rejects_trailing_zlib_data(self):
        b=bytearray(archive());b.extend(b'extra');struct.pack_into('<I',b,76,len(b)-88)
        a=Arc(b)
        with self.assertRaises(ValueError):a.read(a.members[0])

    def test_mloc_preserves_unknown_and_zero_values(self):
        self.assertEqual(mloc(b'mloc'+struct.pack('<I',1)+b'\x03\x00\x09\xff'),[0,9,255])
        with self.assertRaises(ValueError):mloc(b'mloc'+struct.pack('<I',1)+b'\x02\x09')

    def test_gui_property_pools_and_count_flags(self):
        g=Gui(gui_fixture())
        self.assertEqual(g.objects[0]['properties'],{'PosX':-12.5,'Size':[16,8,0,0]})
        self.assertEqual(g.instances[0]['properties'],g.objects[0]['properties'])

    def test_gui_rejects_invalid_property_range(self):
        b=gui_fixture();struct.pack_into('<I',b,0x130+24,100)
        with self.assertRaises(ValueError):Gui(b)

    def test_gui_rejects_string_outside_file(self):
        b=gui_fixture();struct.pack_into('<I',b,0x130+16,0x1000)
        with self.assertRaises(ValueError):Gui(b)

    def test_gui_unknown_array_not_guessed(self):
        b=gui_fixture();struct.pack_into('<I',b,0x180,0x104)
        self.assertEqual(Gui(b).objects[0]['properties']['PosX'],{'unresolved_type':0x104,'raw':0})

    def test_hierarchy_does_not_follow_roots_next_floor(self):
        r=[dict(name='floor1',raw=[0,0,2,1]),dict(name='room',raw=[0,0,0xffffffff,0xffffffff]),dict(name='floor2',raw=[0,0,0xffffffff,0xffffffff])]
        self.assertEqual([n['name'] for n,p in descendants(r,0)],['floor1','room'])

    def test_hierarchy_cycle_and_bad_reference(self):
        for link in [0,99]:
            with self.subTest(link=link),self.assertRaises(ValueError):
                list(descendants([dict(raw=[0,0,0xffffffff,link])],0))

    def test_texture_bc3_known_red_block(self):
        # BC3 alpha=255, RGB565 red, selector zero for every pixel.
        payload=bytes([255,0])+bytes(6)+struct.pack('<HHI',0xf800,0,0)
        b=struct.pack('<4s4I',b'TEX\0',0x2000209d,1|(4<<6)|(4<<19),0x11801,20)+payload
        im=decode_texture(b)
        self.assertEqual(im.size,(4,4))
        self.assertEqual(im.getpixel((2,2)),(255,0,0,255))
        with self.assertRaises(ValueError):decode_texture(b[:-1])

    def test_texture_unknown_codec_refused(self):
        b=struct.pack('<4s4I',b'TEX\0',0x2000209d,1|(4<<6)|(4<<19),0x12b01,20)+bytes(16)
        with self.assertRaises(ValueError):decode_texture(b)


if __name__=='__main__':unittest.main()

from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/inspect'))
from inspect_game import pe_info


class InventoryTest(unittest.TestCase):
    def test_pe32_inventory_uses_section_table_and_build_string(self):
        b=bytearray(0x600);b[:2]=b'MZ';struct.pack_into('<I',b,0x3c,0x80)
        b[0x80:0x84]=b'PE\0\0'
        struct.pack_into('<HHIIIHH',b,0x84,0x14c,1,0,0,0,224,0x102)
        opt=0x98;struct.pack_into('<H',b,opt,0x10b)
        struct.pack_into('<I',b,opt+16,0x1000);struct.pack_into('<I',b,opt+28,0x400000)
        struct.pack_into('<8sIIII',b,opt+224,b'.text',0x200,0x1000,0x200,0x200)
        build=b'MasterRelease synthetic fixture\0';b[0x450:0x450+len(build)]=build
        r=pe_info(b)
        self.assertEqual(r['image_base'],0x400000)
        self.assertEqual(r['sections'][0]['name'],'.text')
        self.assertEqual(r['sections'][0]['raw_offset'],0x200)
        self.assertEqual(r['build_string'],'MasterRelease synthetic fixture')
        self.assertFalse(r['bind_present']);self.assertEqual(r['imports'],[])

    def test_truncated_pe_rejected(self):
        with self.assertRaises(ValueError):pe_info(b'MZ')


if __name__=='__main__':unittest.main()

from pathlib import Path
import math
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'emulator'))
from build_core import build
from core import Core


@unittest.skipUnless(shutil.which('clang'),'Clang required for shared C math tests')
class CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.core=Core(build(Path(cls.directory.name)/'core.dylib'))

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def test_offcentre_endpoints_and_midpoint(self):
        t=self.core.transform(0,(240,363));self.assertEqual((t.scale,t.translate_x,t.translate_y),(1,0,0))
        t=self.core.transform(1,(240,363));self.assertEqual((t.scale,t.translate_x,t.translate_y),(3,1200,-9))
        t=self.core.transform(0.5,(1050,355));self.assertEqual((t.scale,t.translate_x,t.translate_y),(2,-615,7.5))

    def test_scale_rounding_to_one_resets_translation(self):
        t=self.core.transform(1e-9,(240,363));self.assertEqual((t.scale,t.translate_x,t.translate_y),(1,0,0))

    def test_quad_centre_and_affine_matrix(self):
        matrix=[3,0,0,0,0,3,0,0,0,0,1,0,640,360,0,1]
        q=self.core.quad(60,48,5,0,matrix)
        self.assertEqual(q,[550,288,0,0,550,432,0,0,730,432,0,0,730,288,0,0])

    def test_quad_rejects_undefined_anchor_and_bad_matrix(self):
        matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
        for anchor in [3,7,11,12,255]:
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):self.core.quad(10,10,anchor,0,matrix)
        with self.assertRaises(ValueError):self.core.quad(10,10,5,0,matrix[:-1])
        matrix[0]=math.inf
        with self.assertRaises(ValueError):self.core.quad(10,10,5,0,matrix)

    def test_uv_half_texel_and_reversed_rectangle(self):
        self.assertEqual(self.core.uv([0,0,60,48],0),[0.5,0.5,59.5,0.5,0.5,47.5,59.5,47.5])
        self.assertEqual(self.core.uv([60,48,0,0],1),[59.5,47.5,0.5,47.5,59.5,0.5,0.5,0.5])
        self.assertEqual(self.core.uv([0,0,60,48],2),[0,0,60,0,0,48,60,48])
        with self.assertRaises(ValueError):self.core.uv([0,0,math.inf,1],0)

    def test_invalid_and_overflow_inputs_rejected(self):
        for progress,focus in [(-1,(640,360)),(2,(640,360)),(math.nan,(640,360)),(0,(math.inf,360)),(1,(3e38,360))]:
            with self.subTest(progress=progress,focus=focus),self.assertRaises(ValueError):self.core.transform(progress,focus)


if __name__=='__main__':unittest.main()

"""Candidate 48: the overlay never redraws a closed map's last capture, at any fade speed (user 2026-11-06, RE0.NoUIWait FadeSpeed=3)."""
import ctypes,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from core import Core
class Gate(unittest.TestCase):
 def setUp(self):
  self.core=Core();f=self.core.library.re0_present_gate;f.argtypes=[ctypes.POINTER(ctypes.c_uint),ctypes.c_uint,ctypes.c_int,ctypes.c_int];f.restype=ctypes.c_int
  self.state=ctypes.c_uint(0);self.f=lambda gen,clear,live=1:f(ctypes.byref(self.state),gen,clear,live)
 def test_close_then_fade_back_to_clear_draws_nothing(self):
  # Present outpaces map draws: the same capture is redrawn until the fade rises. Any number of Presents with the fade up, then clear again: nothing, whatever the speed.
  for presents_with_fade_up in (1,2,5,60): # 20x, 3x and 1x original fade lengths in Presents
   self.setUp();self.assertEqual([self.f(1,1) for _ in range(4)],[1,1,1,1])
   self.assertEqual([self.f(1,0) for _ in range(presents_with_fade_up)],[0]*presents_with_fade_up)
   self.assertEqual([self.f(1,1) for _ in range(6)],[0]*6)
 def test_a_map_draw_after_the_fade_draws_again(self):
  self.f(1,1);self.f(1,0);self.assertEqual(self.f(1,1),0);self.assertEqual(self.f(2,1),1);self.assertEqual(self.f(2,1),1)
 def test_reopening_during_the_fade_in(self):
  self.assertEqual([self.f(g,0) for g in (1,2,3)],[0,0,0]);self.assertEqual(self.f(4,1),1)
 def test_map_not_live_holds_back_and_stays_stale(self):
  self.f(1,1);self.assertEqual(self.f(2,1,0),0);self.assertEqual(self.f(2,1,1),0);self.assertEqual(self.f(3,1,1),1)
if __name__=='__main__':unittest.main()

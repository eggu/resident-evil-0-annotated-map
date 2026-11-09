import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AnnotationTests(unittest.TestCase):
 def test_portable_core(self):
  with tempfile.TemporaryDirectory() as d:
   exe=Path(d)/'check'
   subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',str(ROOT/'tests/test_annotation.c'),str(ROOT/'src/core/annotation.c'),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)

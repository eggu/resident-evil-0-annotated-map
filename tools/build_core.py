"""Build the shared map math for host-side inspection; does not build or install an ASI."""
from pathlib import Path
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def build(output):
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O2','-ffp-contract=off',
                    '-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',
                    str(ROOT/'src/core/map_transform.c'),str(ROOT/'src/core/annotation.c'),str(ROOT/'src/core/frame.c'),'-o',str(output)],check=True)
    return output


WASM_CC='/opt/homebrew/opt/llvm/bin/clang'
def build_wasm(output):
    """frame.c and friends for the review page; the ASI links the same sources."""
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PATH='/opt/homebrew/opt/lld/bin:'+os.environ['PATH'])
    subprocess.run([WASM_CC,'--target=wasm32','-std=c11','-O2','-nostdlib','-ffreestanding','-Wall','-Wextra','-Werror','-Wno-unused-const-variable','-I',str(ROOT/'src/wasm/include'),'-Wl,--no-entry','-Wl,--strip-debug',*[f'-Wl,--export={n}' for n in ('re0_wasm_settings','re0_wasm_seen','re0_wasm_marker_off','re0_wasm_boxes','re0_wasm_ops','re0_wasm_key','re0_wasm_frame','re0_wasm_obstacles','re0_wasm_kept','re0_wasm_flags','re0_wasm_met','re0_wasm_arrange_rows','re0_wasm_arrange_set','re0_wasm_arrange_mismatches','re0_wasm_done','re0_wasm_room_state','re0_wasm_marker_on','re0_wasm_set_frame','re0_wasm_chrome')],
                    str(ROOT/'src/wasm/glue.c'),str(ROOT/'src/core/frame.c'),str(ROOT/'src/core/annotation.c'),'-o',str(output)],check=True,env=env)
    return output


if __name__=='__main__':
    print(build(ROOT/'local'/('libre0map.dylib' if sys.platform=='darwin' else 'libre0map.so')))

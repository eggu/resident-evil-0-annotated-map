"""Static RE0 GUI scene preview. Runtime visibility/zoom and animation are unverified."""
import argparse
import io
import json
import math
from pathlib import Path
import struct
import sys
from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT/'tools/inspect'))
from resources import Arc, Gui, texture_info, sha256


def decode_texture(data):
    info = texture_info(data)
    formats = {0x14: (b'DXT1', 8), 0x18: (b'DXT5', 16)}
    if info['format'] not in formats:
        raise ValueError(f"unverified TEX codec {info['format']:#x}")
    fourcc, block = formats[info['format']]
    w, h = info['width'], info['height']
    size = ((w+3)//4) * ((h+3)//4) * block
    start = info['offset']
    if start + size > len(data):
        raise ValueError('truncated TEX mip zero')
    header = (struct.pack('<7I', 124, 0xa1007, h, w, size, 0, 1) + bytes(44)
              + struct.pack('<8I', 32, 4, int.from_bytes(fourcc, 'little'), 0, 0, 0, 0, 0)
              + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
    image = Image.open(io.BytesIO(b'DDS '+header+data[start:start+size]))
    return image.convert('RGBA')


def door_ink(game, rect):
    """Painted part of a door sprite, as (left, top, right, bottom) in its texels. Codec 0x2b holds the shape in the DXT5 green channel; the sprite's quad has a transparent margin."""
    if game not in _door_sheets:
        arc = Arc((game/'nativePC/arc/ui/map_eng.arc').read_bytes())
        data = arc.read(next(m for m in arc.members if m.name.endswith('map_door_ID_HQ')))
        info = texture_info(data)
        if info['format'] != 0x2b:
            raise ValueError('door sheet is no longer codec 0x2b')
        w, h = info['width'], info['height']
        size = ((w+3)//4) * ((h+3)//4) * 16
        header = (struct.pack('<7I', 124, 0xa1007, h, w, size, 0, 1) + bytes(44)
                  + struct.pack('<8I', 32, 4, int.from_bytes(b'DXT5', 'little'), 0, 0, 0, 0, 0)
                  + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
        _door_sheets[game] = Image.open(io.BytesIO(b'DDS '+header+data[info['offset']:info['offset']+size])).convert('RGBA').getchannel('G')
    box = _door_sheets[game].crop(tuple(int(v) for v in rect)).point(lambda v: 255 if v > 64 else 0).getbbox()
    if box is None:
        raise ValueError('door sprite paints nothing')
    return box


_door_sheets = {}


def descendants(records, index):
    """GUI next-sibling (+8), first-child (+12) indices; reject cycles/sharing."""
    visited = set()
    def walk(i, parents):
        while i != 0xffffffff:
            if not 0 <= i < len(records) or i in visited:
                raise ValueError('invalid GUI hierarchy reference/cycle')
            visited.add(i)
            row = records[i]
            yield row, parents
            yield from walk(row['raw'][3], parents + [row])
            i = row['raw'][2]
    # Include this root and children, not the root's next floor sibling.
    if not 0 <= index < len(records):
        raise ValueError('GUI hierarchy root outside table')
    root = records[index]
    visited.add(index)
    yield root, []
    yield from walk(root['raw'][3], [root])


def load_scene(game, region):
    arc = Arc((game/'nativePC/arc/ui/map_eng.arc').read_bytes())
    gui_member = next((m for m in arc.members if m.kind == 0x22948394 and m.name.endswith('\\map_'+region)), None)
    if gui_member is None:
        raise ValueError('region GUI not found')
    gui_data = arc.read(gui_member)
    return arc, Gui(gui_data), dict(member=gui_member.name, sha256=sha256(gui_data))


def render(game, region, floor, zoom=1, pan=(0, 0), labels=False, native_progress=None, focus=(640,360), core_path=None, group_suffix='', geometry_only=False, sprites=None):
    if not math.isfinite(zoom) or not 0.25 <= zoom <= 4 or not all(math.isfinite(x) for x in pan):
        raise ValueError('invalid diagnostic zoom/pan')
    from core import Core
    core = Core(core_path)
    native_scale, native_x, native_y = 1.0, 0.0, 0.0
    if native_progress is not None:
        native = core.transform(native_progress, focus)
        native_scale, native_x, native_y = native.scale, native.translate_x, native.translate_y
    arc, gui, source = load_scene(game, region)
    group = 'Null_' + region + floor + group_suffix
    roots = [r for r in gui.instances if r['name'] == group]
    if len(roots) != 1:
        raise ValueError(f'floor group not found: {group}')
    if not 1 <= gui.width <= 8192 or not 1 <= gui.height <= 8192:
        raise ValueError('invalid GUI canvas dimensions')
    image = Image.new('RGBA', (gui.width, gui.height), (160, 155, 140, 255))
    trace = dict(status='provisional-static-resource-preview', scope='room-floor-groups-only; door groups excluded', source=source, region=region, floor=floor,
                 transform='diagnostic canvas centre; not native runtime zoom/viewport',
                 zoom=zoom, pan=list(pan), drawn=[], omitted=[], labels=labels,
                 texture_sources=[],
                 native_setter_layer=None if native_progress is None else dict(progress=native_progress, focus=list(focus), scale=native_scale, x=native_x, y=native_y))
    texture_members = {m.name: m for m in arc.members if m.kind == 0x241f5deb}
    cache = {}
    shared = []
    for instance, parents in descendants(gui.instances, roots[0]['index']):
        ip = instance['properties']
        anim = gui.animations.get(ip.get('AnimationId'))
        if anim is None:
            if instance['name'].startswith('i_'):
                trace['omitted'].append(dict(instance=instance['name'], reason='animation unresolved'))
            continue
        chain = parents + [instance]
        if not all(r['properties'].get('Visible', True) for r in chain):
            continue
        # Current map resources use unit instance scale. Reject unsupported transforms, never approximate silently.
        if any(r['properties'].get('SclX', 1) != 1 or r['properties'].get('SclY', 1) != 1
               or r['properties'].get('Rotation', 0) != 0 for r in chain):
            trace['omitted'].append(dict(instance=instance['name'], reason='instance scale/rotation not evaluated'))
            continue
        x = sum(r['properties'].get('PosX', 0) for r in chain)
        y = sum(r['properties'].get('PosY', 0) for r in chain)
        objects = list(descendants(gui.objects, anim['root']))
        for obj, objparents in sorted(objects, key=lambda row: row[0]['properties'].get('Priority', 0)):
            op = obj['properties']
            if 'Texture' not in op or not all(r['properties'].get('Visible', True) for r in objparents+[obj]):
                continue
            if op.get('Reverse', False) or op.get('Rotation', 0) != 0 or op.get('ControlPoint') not in (0,1,2,4,5,6,8,9,10):
                trace['omitted'].append(dict(instance=instance['name'], object=obj['name'], reason='object transform unsupported'))
                continue
            if geometry_only:
                # Door art uses a refused codec, but where it is drawn does not depend on its pixels.
                size = op.get('Size')
                cx, cy = gui.width/2 + x + op.get('PosX', 0), gui.height/2 + y + op.get('PosY', 0)
                quad = core.quad(size[0],size[1],op['ControlPoint'],0,[1,0,0,0,0,1,0,0,0,0,1,0,cx,cy,0,1])
                qx, qy = quad[0::4], quad[1::4]
                box = [min(qx), min(qy), max(qx), max(qy)]
                rect = op.get('mTextureRect')
                ink = door_ink(game, rect) if isinstance(rect, list) and 'map_door' in gui.textures.get(op['Texture'], dict(path=''))['path'] else None
                # Same scale in x and y: quads are 1:1 with texels here.
                trace['drawn'].append(dict(instance=instance['name'], object=obj['name'], canvas_box=box, ink_box=[box[0]+ink[0], box[1]+ink[1], box[0]+ink[2], box[1]+ink[3]] if ink else box))
                continue
            ref = gui.textures.get(op['Texture'])
            if not ref:
                trace['omitted'].append(dict(instance=instance['name'], object=obj['name'], reason='texture ID unresolved'))
                continue
            if ref['path'] not in cache:
                owner, member, filename = arc, texture_members.get(ref['path']), 'map_eng.arc'
                if member is None:
                    if not shared:
                        for filename_shared in ['map.arc','map_jpn.arc']:
                            path = game/'nativePC/arc/ui'/filename_shared
                            if path.exists():
                                shared.append((filename_shared, Arc(path.read_bytes())))
                    for filename_shared, candidate in shared:
                        found = next((m for m in candidate.members if m.kind == 0x241f5deb and m.name == ref['path']), None)
                        if found is not None:
                            owner, member, filename = candidate, found, filename_shared
                            break
                if member is None:
                    trace['omitted'].append(dict(instance=instance['name'], object=obj['name'], reason='exact texture resource not found'))
                    continue
                try:
                    payload = owner.read(member)
                    cache[ref['path']] = decode_texture(payload)
                    trace['texture_sources'].append(dict(resource=ref['path'],archive=filename,sha256=sha256(payload)))
                except ValueError as e:
                    trace['omitted'].append(dict(instance=instance['name'], object=obj['name'], reason=str(e)))
                    continue
            rect = op.get('mTextureRect')
            size = op.get('Size')
            if not isinstance(rect, list) or not isinstance(size, list):
                raise ValueError('sprite rectangle/size unresolved')
            tex = cache[ref['path']]
            left, top, right, bottom = rect
            if not 0 <= left < right <= tex.width or not 0 <= top < bottom <= tex.height:
                raise ValueError('sprite UV rectangle outside texture')
            w, h = size[:2]
            if not 0 < w <= 8192 or not 0 < h <= 8192 or not all(math.isfinite(v) for v in (w,h,x,y)):
                raise ValueError('invalid sprite geometry')
            # shortcut: native parent matrices/viewport remain unverified; the supplied canvas matrix is diagnostic.
            cx = gui.width/2 + (native_scale*(x + op.get('PosX', 0)) + native_x + pan[0])*zoom
            cy = gui.height/2 + (native_scale*(y + op.get('PosY', 0)) + native_y + pan[1])*zoom
            scale = zoom*native_scale
            matrix = [scale,0,0,0,0,scale,0,0,0,0,1,0,cx,cy,0,1]
            quad = core.quad(w,h,op['ControlPoint'],0,matrix)
            qx, qy = quad[0::4], quad[1::4]
            qleft,qtop,qright,qbottom = min(qx),min(qy),max(qx),max(qy)
            tw, th = max(1,round(qright-qleft)), max(1,round(qbottom-qtop))
            if tw > 16384 or th > 16384 or tw*th > 64*1024*1024:
                raise ValueError('diagnostic sprite exceeds image allocation limit')
            native_uv = core.uv(rect,op.get('SamplerState',0))
            extent = (native_uv[0],native_uv[1],native_uv[6],native_uv[7])
            tile = tex.transform((tw,th),Image.Transform.EXTENT,extent,Image.Resampling.BILINEAR)
            px, py = round(qleft), round(qtop)
            if sprites is not None:sprites.append(dict(instance=instance['name'],texture=ref['path'],box=(px,py),tile=tile))
            if px < image.width and py < image.height and px+tile.width > 0 and py+tile.height > 0:
                image.alpha_composite(tile, (px,py))
            trace['drawn'].append(dict(instance=instance['name'], object=obj['name'], texture=ref['path'],
                                       gui_position=[x,y], canvas_anchor=[cx,cy], quad=quad, native_uv=native_uv, canvas_box=[px,py,px+tile.width,py+tile.height], uv=rect))
        if labels:
            ImageDraw.Draw(image).text((round(gui.width/2+(native_scale*x+native_x+pan[0])*zoom), round(gui.height/2+(native_scale*y+native_y+pan[1])*zoom)),
                                       instance['name'][2:], fill=(180,0,0,255), anchor='mm')
    return image, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--region', choices=['tr','sh','dm','ch','bt','pl'], required=True)
    parser.add_argument('--floor', required=True, help='native suffix, e.g. 1f, 2f, b1, roof')
    parser.add_argument('--zoom', type=float, default=1, help='diagnostic scale, not native zoom reproduction')
    parser.add_argument('--pan', type=float, nargs=2, default=(0,0))
    parser.add_argument('--native-progress', type=float, help='apply verified native setter math (0..1); viewport remains provisional')
    parser.add_argument('--focus', type=float, nargs=2, default=(640,360))
    parser.add_argument('--core', type=Path, default=PROJECT/'local'/('libre0map.dylib' if sys.platform=='darwin' else 'libre0map.so'))
    parser.add_argument('--labels', action='store_true', help='diagnostic internal IDs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(PROJECT/'local'):
        parser.error('resource-derived previews must stay under project local/')
    image, trace = render(args.game.resolve(), args.region, args.floor, args.zoom, args.pan, args.labels, args.native_progress, args.focus, args.core)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    output.with_suffix('.json').write_text(json.dumps(trace, indent=2)+'\n')
    print(f"{args.region}/{args.floor}: {len(trace['drawn'])} sprites, {len(trace['omitted'])} omissions; {args.output}")


if __name__ == '__main__':
    main()

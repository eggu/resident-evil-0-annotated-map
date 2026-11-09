"""Inventory local game files without changing them or extracting payloads."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
from resources import Arc, Gui, mloc, sha256, texture_info, unpack

PROJECT = Path(__file__).resolve().parents[2]


def pe_info(data):
    # Reuse the workspace PE32 validator; the report is not a standalone packaged tool.
    path = PROJECT.parents[1] / 'common/re-mod-presets/tools/pe.py'
    spec = importlib.util.spec_from_file_location('workspace_pe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pe = module.PE(data)
    at = pe.unpack('<I', 0x3c)[0] + 24
    imports_rva, _ = pe.unpack('<II', at + 104)
    imports = []
    if imports_rva:
        cursor = pe.offset(imports_rva)
        for _ in range(len(data) // 20):
            desc = pe.unpack('<5I', cursor)
            if not any(desc):
                break
            start = pe.offset(desc[3])
            end = data.find(b'\0', start, start + 256)
            if end < 0:
                raise ValueError('invalid PE import name')
            imports.append(data[start:end].decode('ascii'))
            cursor += 20
        else:
            raise ValueError('unterminated PE imports')
    sections = []
    for i, (rva, size, raw, rawsize) in enumerate(pe.sections):
        section_at = at + pe.unpack('<H', at - 4)[0] + i * 40
        sections.append(dict(name=data[section_at:section_at+8].split(b'\0')[0].decode(),
                             rva=rva, size=size, raw_offset=raw, raw_size=rawsize))
    build = None
    marker = b'MasterRelease '
    start = data.find(marker)
    if start >= 0:
        end = data.find(b'\0', start, start+128)
        if end >= 0:
            build = data[start:end].decode('ascii')
    return dict(architecture='x86', image_base=pe.unpack('<I', at+28)[0],
                entry_rva=pe.entry, sections=sections, imports=imports,
                build_string=build, bind_present=any(s['name']=='.bind' for s in sections))


def inspect(game):
    exe = (game/'re0hd.exe').read_bytes()
    report = dict(schema_version=1, evidence='static',
                  exe=dict(file='re0hd.exe', size=len(exe), sha256=sha256(exe), **pe_info(exe)),
                  archives=[], mods=[])
    for name in ['map/maploc.arc', 'ui/map.arc', 'ui/map_eng.arc']:
        path = game/'nativePC/arc'/name
        raw = path.read_bytes()
        arc = Arc(raw)
        archive = dict(file=str(path.relative_to(game)), sha256=sha256(raw), members=[])
        for member in arc.members:
            data = arc.read(member)
            item = dict(name=member.name, kind=f'{member.kind:08x}', size=len(data), sha256=sha256(data))
            if member.kind == 0x44c8ac26:
                item['location_bytes'] = mloc(data)
            elif member.kind == 0x241f5deb:
                item['texture'] = texture_info(data)
            elif member.kind == 0x22948394:
                gui = Gui(data)
                item['gui'] = dict(width=gui.width, height=gui.height,
                                   objects=len(gui.objects), instances=len(gui.instances),
                                   animations=len(gui.animations), textures=len(gui.textures),
                                   floor_groups=[r['name'] for r in gui.instances if r['name'].startswith('Null_')])
            archive['members'].append(item)
        report['archives'].append(archive)
    for path in sorted((game/'scripts').glob('*.asi')):
        data = path.read_bytes()
        report['mods'].append(dict(file=str(path.relative_to(game)), sha256=sha256(data)))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    game, output = args.game.resolve(), args.output.resolve()
    if output.is_relative_to(game):
        parser.error('report must be outside the game directory')
    report = inspect(game)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(f"Inspected {len(report['archives'])} archives; report: {args.output}")


if __name__ == '__main__':
    main()

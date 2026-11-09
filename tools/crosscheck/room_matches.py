"""Check curated place-to-native mappings for integrity; does not re-review their images."""
import argparse
import json
from pathlib import Path


def validate(native,external,matches):
    pieces={p['id']:p for p in native['map_pieces']}
    locations={p['id']:p for p in external['locations']}
    sources={s.get('member'):s['sha256'] for s in native['sources'] if 'member' in s}
    used_pieces=set();used_locations=set()
    for claim in matches['claims']:
        key=claim['external_id']
        if key not in locations or key in used_locations:raise ValueError('missing or duplicate external location')
        used_locations.add(key);source=locations[key]
        if source['region']!=claim['region'] or key.split('/')[0].rsplit('-',1)[-1]!=claim['floor']:
            raise ValueError('external region/floor identity mismatch')
        if claim['name_en']!=source['name'] or claim['evidence']['source_url']!=source['url']:
            raise ValueError('external room identity/name changed; re-review needed')
        if claim['result']!='geometry-and-floor-reviewed' or not claim['unverified']:
            raise ValueError('curated claim must retain its bounded verification scope')
        if not claim['native_pieces']:raise ValueError('mapping has no native piece')
        for piece in claim['native_pieces']:
            if piece not in pieces or piece in used_pieces:raise ValueError('missing or multiply assigned native piece')
            used_pieces.add(piece);row=pieces[piece]
            if row['region']!=claim['region'] or row['floor']!=claim['floor'] or row['native_room_id'] is None:
                raise ValueError('native room/floor identity mismatch')
            if sources.get(row['gui_member'])!=claim['evidence']['native_gui_sha256']:
                raise ValueError('native GUI source changed; re-review needed')
        # Same native room shown on another floor/map (tower ground level, cable car at the factory end).
        for alias in claim.get('alias_pieces',[]):
            piece=alias['piece']
            if piece not in pieces or piece in used_pieces or not alias.get('reason'):raise ValueError('invalid alias piece')
            used_pieces.add(piece)
            if pieces[piece]['native_room_id']!=pieces[claim['native_pieces'][0]]['native_room_id']:raise ValueError('alias must share native room')
        for place in claim.get('also_covers',[]):
            if place not in locations or place in used_locations:raise ValueError('invalid covered place')
            used_locations.add(place)
    return dict(evidence='curated-mapping-integrity-only',
                locations_total=len(locations),locations_reviewed=len(used_locations),
                native_pieces_total=len(pieces),native_pieces_named=len(used_pieces),
                remaining_external_ids=sorted(set(locations)-used_locations),
                remaining_native_pieces=sorted(set(pieces)-used_pieces),
                caveat='Room names/floor geometry only; no item, door, mode or eligibility claim')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True);p.add_argument('--external',type=Path,required=True)
    p.add_argument('--matches',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=validate(*[json.loads(path.read_text()) for path in [a.native,a.external,a.matches]])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f"Curated mappings: {report['locations_reviewed']}/{report['locations_total']} external places, {report['native_pieces_named']}/{report['native_pieces_total']} native pieces; integrity checked")


if __name__=='__main__':main()

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/crosscheck'))
from room_matches import validate


def fixtures():
    native=dict(map_pieces=[dict(id='a',region='tr',floor='1f',native_room_id=0,gui_member='gui'),
                            dict(id='b',region='tr',floor='1f',native_room_id=0,gui_member='gui')],
                sources=[dict(member='gui',sha256='synthetic')])
    external=dict(locations=[dict(id='train-1f/room',region='tr',name='Room',url='https://example.invalid/synthetic')])
    matches=dict(claims=[dict(external_id='train-1f/room',name_en='Room',region='tr',floor='1f',native_pieces=['a','b'],
                             result='geometry-and-floor-reviewed',unverified=['eligibility'],
                             evidence=dict(source_url='https://example.invalid/synthetic',native_gui_sha256='synthetic'))])
    return native,external,matches


class RoomMatchesTest(unittest.TestCase):
    def test_sections_are_pieces_not_distinct_external_places(self):
        report=validate(*fixtures())
        self.assertEqual((report['locations_reviewed'],report['native_pieces_named']),(1,2))

    def test_wrong_floor_and_changed_native_source_rejected(self):
        for key,value in [('floor','2f'),('native_room_id',None)]:
            n,e,m=fixtures();n['map_pieces'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(n,e,m)
        n,e,m=fixtures();m['claims'][0]['floor']='2f'
        for row in n['map_pieces']:row['floor']='2f'
        with self.assertRaises(ValueError):validate(n,e,m)
        n,e,m=fixtures();n['sources'][0]['sha256']='changed'
        with self.assertRaises(ValueError):validate(n,e,m)

    def test_changed_external_identity_and_duplicate_claim_rejected(self):
        n,e,m=fixtures();e['locations'][0]['name']='Changed'
        with self.assertRaises(ValueError):validate(n,e,m)
        n,e,m=fixtures();m['claims'].append(deepcopy(m['claims'][0]))
        with self.assertRaises(ValueError):validate(n,e,m)


    def test_alias_requires_same_native_room(self):
        n,e,m=fixtures();n['map_pieces'].append(dict(id='c',region='bt',floor='b1',native_room_id=0,gui_member='other'))
        m['claims'][0]['alias_pieces']=[dict(piece='c',reason='synthetic')]
        self.assertEqual(validate(n,e,m)['native_pieces_named'],3)
        n['map_pieces'][-1]['native_room_id']=9
        with self.assertRaises(ValueError):validate(n,e,m)


if __name__=='__main__':unittest.main()

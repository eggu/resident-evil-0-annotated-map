from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/crosscheck'))
from floor_catalogue import compare,source_floors
from external_locations import Locations


class CrosscheckTest(unittest.TestCase):
    def test_floor_only_claim_rejects_irrelevant_headings(self):
        html='<h2>Game sections</h2><h2>Train <b>1F</b></h2><h2>Train Roof</h2><h2>Train 1F items</h2>'
        self.assertEqual(source_floors(html,'Train'),['1f','roof'])
        self.assertEqual(compare(['1f'],['1f','roof'])['missing_from_native'],['roof'])

    def test_changed_source_markup_fails(self):
        with self.assertRaises(ValueError):source_floors('<h3>Train 1F</h3>','Train')

    def test_repeated_floor_heading_fails(self):
        with self.assertRaises(ValueError):source_floors('<h2>Train 1F</h2>'*2,'Train')

    def test_split_areas_keep_one_external_identity(self):
        parser=Locations()
        area='<area href="/resident-evil-zero/maps/train/train-1f/test" data-id="train-1f/test" data-name="Test" shape="rect" coords="1,2,3,4">'
        parser.feed('<map name="synthetic">'+area+area+'</map>')
        self.assertEqual(len(parser.locations),1)
        self.assertEqual(len(parser.locations['train-1f/test']['areas']),2)
        self.assertEqual(parser.locations['train-1f/test']['areas'][0]['map'],'synthetic')

    def test_bad_source_shape_fails(self):
        parser=Locations()
        with self.assertRaises(ValueError):
            parser.feed('<area href="/resident-evil-zero/maps/test" data-id="test" data-name="Test" shape="poly" coords="1,2,3">')


if __name__=='__main__':unittest.main()

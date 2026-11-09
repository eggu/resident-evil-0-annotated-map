"""Extract source room identities and image-map geometry, without assigning native IDs."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from floor_catalogue import REGIONS


class Locations(HTMLParser):
    def __init__(self):
        super().__init__();self.locations={};self.map=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='map':self.map=a.get('name')
        if tag!='area' or not a.get('data-id'):return
        if not a.get('href','').startswith('/resident-evil-zero/maps/'):
            raise ValueError('unexpected location URL namespace')
        if not a.get('data-name'):raise ValueError('missing external location name')
        key=a['data-id']
        if not re.fullmatch(r'[a-z0-9/-]+',key):raise ValueError('invalid external location ID')
        coords=[int(x) for x in a.get('coords','').split(',') if x]
        shape=a.get('shape')
        if shape=='rect' and len(coords)!=4 or shape=='poly' and (len(coords)<6 or len(coords)%2):
            raise ValueError('invalid external location geometry')
        if shape=='circle' and (len(coords)!=3 or coords[2]<=0):raise ValueError('invalid external circle')
        if shape not in ('rect','poly','circle'):raise ValueError('unsupported external location shape')
        row=self.locations.setdefault(key,dict(id=key,name=a['data-name'],url='https://www.evilresource.com'+a['href'],areas=[]))
        if row['name']!=a['data-name']:raise ValueError('conflicting names for source location')
        row['areas'].append(dict(map=self.map,shape=shape,coords=coords))
    def handle_endtag(self,tag):
        if tag=='map':self.map=None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checked-on',required=True)
    a=p.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',a.checked_on):p.error('invalid checked-on date')
    rows=[]
    for region,(slug,label) in REGIONS.items():
        parser=Locations();parser.feed((a.sources/(region+'.html')).read_text())
        if not parser.locations:raise ValueError('no locations found')
        for row in parser.locations.values():
            row.update(region=region,native_id=None,result='native-mapping-unverified',checked_on=a.checked_on,
                       source_page='https://www.evilresource.com/resident-evil-zero/maps/'+slug)
            rows.append(row)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(schema_version=1,claim='external-location-catalogue-only',
                                       edition='HD applicability not independently confirmed',locations=rows),indent=2)+'\n')
    print(f'External locations: {len(rows)}; native ID matches: 0 (not inferred)')


if __name__=='__main__':main()

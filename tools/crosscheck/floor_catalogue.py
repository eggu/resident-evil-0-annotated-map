"""Compare native GUI floor groups with explicitly supplied source HTML.

Network fetching is deliberately separate so a source change cannot silently alter a report.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'emulator'))
from render import load_scene

REGIONS={
 'tr':('train','Train'), 'sh':('training-facility','Training Facility'),
 'dm':('facility-basement','Facility Basement'), 'ch':('laboratory','Laboratory'),
 'bt':('factory','Factory'), 'pl':('treatment-plant','Treatment Plant'),
}


class Headings(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.text=[];self.headings=[]
    def handle_starttag(self,tag,attrs):
        if tag=='h2':self.active=True;self.text=[]
    def handle_data(self,data):
        if self.active:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='h2' and self.active:
            self.headings.append(' '.join(''.join(self.text).split()));self.active=False


def source_floors(html,label):
    parser=Headings();parser.feed(html)
    out=[]
    for heading in parser.headings:
        if not heading.startswith(label+' '):continue
        suffix=heading[len(label)+1:]
        if not re.fullmatch(r'(?:B[1-9]|[1-9]F|Roof)',suffix):continue
        normalized=suffix.lower()
        if normalized in out:raise ValueError('duplicate external floor heading')
        out.append(normalized)
    if not out:raise ValueError('no recognized floor headings; inspect source markup')
    return out


def compare(native,external):
    return dict(native=sorted(native),external=sorted(external),
                missing_from_native=sorted(set(external)-set(native)),
                missing_from_external=sorted(set(native)-set(external)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True,help='directory with region.html files')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checked-on',required=True,help='actual source access date YYYY-MM-DD')
    a=p.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',a.checked_on):p.error('invalid checked-on date')
    if a.output.resolve().is_relative_to(a.game.resolve()):p.error('output must be outside game')
    rows=[]
    for region,(slug,label) in REGIONS.items():
        _,gui,source=load_scene(a.game,region)
        native=[r['name'][len('Null_'+region):] for r in gui.instances
                if r['name'].startswith('Null_'+region) and not r['name'].endswith('_door')]
        external=source_floors((a.sources/(region+'.html')).read_text(),label)
        row=dict(region=region,source_url='https://www.evilresource.com/resident-evil-zero/maps/'+slug,
                 locator='h2 floor headings',checked_on=a.checked_on,native_source=source,
                 claim='floor-catalogue-only',edition='HD applicability not independently confirmed',
                 **compare(native,external))
        row['result']='match' if not row['missing_from_native'] and not row['missing_from_external'] else 'conflict'
        rows.append(row)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(schema_version=1,claims=rows),indent=2)+'\n')
    print(f"Floor catalogue: {sum(x['result']=='match' for x in rows)}/{len(rows)} region matches; no room/item claims")


if __name__=='__main__':main()

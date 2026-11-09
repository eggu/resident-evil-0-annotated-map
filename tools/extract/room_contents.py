"""Extract linked places and contents from private external room pages; keeps facts and URLs, not descriptive prose."""
import argparse,html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import sys;sys.path.insert(0,str(ROOT/'tools/extract'))
from conditions import reward_rank
ITEM=re.compile(r'<li data-gamemode="gm(\d+)">(.*?)</li>',re.S)
MODES={'33':'easy','11':'normal','32':'hard'}
def parse(page):
 """Return (linked ids, contents); raises when the page layout no longer matches instead of returning an empty room."""
 if 'Contents</h2>' not in page and 'no contents' not in page.lower():raise ValueError('room page layout changed')
 linked=[]
 m=re.search(r'linked to the following locations:</p>\s*<ul>(.*?)</ul>',page,re.S)
 if m:linked=re.findall(r'href="/resident-evil-zero/maps/[^/"]+/([^"]+)"',m[1])
 rows=[]
 for mode,body in ITEM.findall(page):
  title=re.search(r'<h\d class="h6[^"]*">(.*?)</h\d>',body,re.S)
  # Descriptions contain links to other things, so only the row's own action link identifies it.
  link=re.search(r'class="actions">\s*<a href="/resident-evil-zero/([a-z-]+)/([^"#]+)"',body)
  if not title or not link:raise ValueError('content row layout changed')
  if mode not in MODES:raise ValueError('unknown game mode '+mode)
  row=dict(name=html.unescape(re.sub(r'<[^>]+>','',title[1])).strip(),kind=link[1],slug=link[2],mode=MODES[mode])
  text=re.search(r'class="text">(.*?)</div>',body,re.S);rank=reward_rank(html.unescape(re.sub(r'<[^>]+>','',text[1]))) if text else None
  rows.append(dict(row,reward_rank=rank) if rank else row)
 return linked,rows
def build(pages):
 external=json.loads((ROOT/'data/external-locations.json').read_text());places=[]
 for l in external['locations']:
  linked,rows=parse((pages/(l['id'].replace('/','__')+'.html')).read_text())
  places.append(dict(id=l['id'],url=l['url'],linked=linked,contents=rows))
 return dict(schema_version=1,evidence='external-room-catalogue',source='https://www.evilresource.com/resident-evil-zero/maps',checked_on='2026-11-03',
  caveat='Initial per-room listing by difficulty; not save state. Edition applicability to the HD build not independently established.',places=places)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pages',type=Path,default=ROOT/'local/external/rooms');p.add_argument('--output',type=Path,default=ROOT/'data/room-contents.json');a=p.parse_args()
 d=build(a.pages);a.output.write_text(json.dumps(d,ensure_ascii=False,indent=1)+'\n')
 print(len(d['places']),'places',sum(len(x['contents']) for x in d['places']),'rows')

"""Inventory of events in every main-game room script: groups that start a cutscene (Demo_Start, PlayMovie) or, with no cutscene, turn an enemy on (SetEnemyFlag x,1). Analysis only.

Groups are walked from their real entry with Scripts.evaluate, one flag forced at a time, so conditions are what the script tests and no neighbouring group is attributed.
script_read means this reading only: nobody has seen the cutscene or the enemy, and what the scene shows is not known. Rules:
excluded: tag 18 (room setup, the same scenes in nearly every room), tag 8 or 30 (item use, has a puzzle mark), or a group outside PLACED whose cutscenes all run from a placed group too.
unresolved: no flag decides that it has happened, so a mark could never hide; or that flag is cleared again by a script, so a mark would return (a repeatable action, not a one-shot).
script_read: done is a flag whose being set stops the event and which a script sets. need is a flag whose being clear stops it. Only the first need is applied to the mark; others are listed.
Position: tag 2 or 14 with volume x of <scene>b, tag 17 the table row of item x, otherwise room level, labelled so. What tags mean is observed over all scripts, see verification/event-audit.md: the native code that selects a group by tag was not found.
"""
import re,struct
from event_disasm import groups
SCENES=('Demo_Start','PlayMovie')
ITEM_USE=(8,30)
PLACED=(2,4,8,12,14,17,30)
def is_room_script(name):return bool(re.fullmatch(r'[a-z]{2}[0-9a-f]{2}',name))
def analyse(s,scene,written):
 """written: flag -> writes (place,value) from Scripts.index. Rows for every group with an event, and its status."""
 _,d=s.members[scene];found=[]
 for index,tag,off,x,y in s.heads(scene):
  if not off:continue
  reach=s.reach(d,off);ops=list(reach.values())
  scenes=[(n,a[0]) for n,a in ops if n in SCENES];spawn=sorted({a[0] for n,a in ops if n=='SetEnemyFlag' and a[1]==1})
  if not scenes and not spawn:continue
  fires=lambda out:any(o[0] in SCENES or (not scenes and o[0]=='SetEnemyFlag' and o[1][1]==1) for o in out)
  done=[];need=[]
  for f in sorted({a[0] for n,a in ops if n=='ResFlag'}):
   at0,at1=fires(s.evaluate(d,off,f,0)),fires(s.evaluate(d,off,f,1))
   if at0 and not at1:done.append(f)
   if at1 and not at0:need.append(f)
  found.append(dict(scene=scene,group=index,tag=tag,x=x,y=y,basis='cutscene' if scenes else 'enemy on',scenes=[f'{n} {v}' for n,v in scenes],enemy_flags=spawn,done_candidates=done,need=need))
 for g in found:
  others={c for o in found if o is not g and o['tag'] in PLACED for c in o['scenes']}
  taken=[f for f in g['done_candidates'] if any(v==1 for _,v in written.get(f,()))]
  cleared=sorted(p for f in taken[:1] for p,v in written.get(f,()) if v==0)
  if g['tag']==18:st,why='excluded','room setup'
  elif g['tag'] in ITEM_USE:st,why='excluded','item use, has a puzzle mark'
  elif g['tag'] not in PLACED and g['scenes'] and all(c in others for c in g['scenes']):st,why='excluded','same cutscenes run from a placed group'
  elif not taken:st,why='unresolved','no flag decides it has happened'
  elif cleared:st,why='unresolved',f'done flag {taken[0]:#x} cleared again by {cleared}'
  else:st,why='script_read',f'done flag {taken[0]:#x}'
  g.update(status=st,reason=why,done=taken[0] if taken else None)
 return found

"""What a loc2 record's condition byte (offset +2) means, from native code in re0hd.exe. One rule for every consumer.

Loader 0x40eb50 stores it as a dword at row+0xc (+3 at row+0x10, +4 at row+0x14, +5 at row+0x1c), so it is one byte, not a u16 with +3.
Spawn 0x410bb0: 0x410c46-0x410c75 returns without an actor unless the byte is 0 or flag 0x312+byte is set (bit test 0x59b8d0, array at [0xdcc014]+0x20).
The game's own map (0x5b6903-0x5b6947) and item list (0x57da2f-0x57da73) use the same test. Setters 0x59ba50/0x59bd50/0x59c320/0x59c980 spawn or remove live rows for flags in that range.
Flags 0x3b2-0x3b4 have one writer, 0x59d2a0, from reward bits of [0xdcbe9c]+0x40 (0x20, 0x100, 0x10); no event script writes them. Those bits come from uGUILeechHunterResult
0x5af6d6: table 0xd9cd98 by rank index, thresholds 0xcdb59c (100, 90, 60, 30, any leeches). Best rank is index 0; letters A-E are by that order and match the catalogue's B and E.
"""
import re
FLAG_BASE=0x312
# byte: (flag, reward bit, rank index, rank letter)
UNLOCK={160:(0x3b2,0x20,1,'B'),161:(0x3b3,0x100,4,'E'),162:(0x3b4,0x10,0,'A')}
# Catalogue wording for the same rewards; 'at least' agrees with 0x5af61e-0x5af7c3 granting index 4 down to the rank earned.
REWARD=re.compile(r'Only appears here after achieving at least an? ([A-E]) Rank in the Leech Hunter')
CONDITIONAL=re.compile(r'\bOnly appears? here\b|\bappears? here after\b',re.I)
def reward_rank(text):
 m=REWARD.search(text);return m[1] if m else None
def catalogue_condition(row):
 """The record byte a catalogue row's reward wording stands for, so room counts follow the same live flag. 0 when it has none."""
 rank=row.get('reward_rank')
 return next((byte for byte,u in UNLOCK.items() if u[3]==rank),0) if rank else 0

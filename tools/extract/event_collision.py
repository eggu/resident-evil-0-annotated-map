"""Read rEventCollision: triangle lists of one trigger volume, then two trailing integers."""
import struct
def parse(data):
 """Raises if the lists do not consume the payload, so a wrong layout cannot pass quietly."""
 at=data.index(b'data\0')+5+24
 lists=struct.unpack_from('<I',data,at)[0]>>8;at+=5;out=[]
 for _ in range(lists):
  _,_,size,tris=struct.unpack_from('<HHII',data,at);at+=12
  if size!=tris*48+8:raise ValueError('collision list size')
  out.append([struct.unpack_from('<4f',data,at+i*16)[:3] for i in range(tris*3)]);at+=tris*48
 kind,tag=struct.unpack_from('<II',data,at);at+=8
 if at!=len(data):raise ValueError(f'collision ended at {at} of {len(data)}')
 return dict(lists=out,kind=kind,tag=tag)

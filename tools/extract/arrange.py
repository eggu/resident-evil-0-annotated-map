"""Read rArrange 'loc2' placement tables (nativePC/arc/arrange/loctbl.arc)."""
import struct
RECORD=32
def parse(data):
 """Room list with decoded records. Raises unless the layout consumes the file, so a wrong layout cannot pass quietly."""
 magic,version,count=struct.unpack_from('<4sII',data,0)
 if magic!=b'loc2' or version!=1:raise ValueError('unsupported loc2 header')
 at=12;rooms=[]
 for _ in range(count):
  room,n=struct.unpack_from('<HH',data,at);at+=4;rows=[]
  for _ in range(n):
   kind,item,a2,a3,f0,f1,amount=struct.unpack_from('<6BH',data,at)
   x,y,z,_,ry,_=struct.unpack_from('<6f',data,at+8)
   rows.append(dict(kind=kind,item=item,a=(a2,a3,f0,f1),amount=amount,pos=(x,y,z),rot=ry));at+=RECORD
  rooms.append(dict(room=room,records=rows))
 if len(data)-at>RECORD:raise ValueError(f'loc2 ended at {at} of {len(data)}')
 return rooms

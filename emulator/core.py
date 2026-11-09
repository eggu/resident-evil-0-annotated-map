"""Host binding to the same C transform function intended for the ASI."""
import ctypes
from pathlib import Path
import sys


class Transform(ctypes.Structure):
    _fields_=[('scale',ctypes.c_float),('translate_x',ctypes.c_float),('translate_y',ctypes.c_float)]


class Box(ctypes.Structure):
    _fields_=[(key,ctypes.c_float) for key in ('l','t','r','b')]
    def values(self): return [self.l,self.t,self.r,self.b]

class Content(ctypes.Structure):
    _fields_=[('category',ctypes.c_ubyte),('easy',ctypes.c_ubyte),('normal',ctypes.c_ubyte),('hard',ctypes.c_ubyte),('ko',ctypes.c_ushort),('en',ctypes.c_ushort),('condition',ctypes.c_ubyte)]

class Settings(ctypes.Structure):
    _fields_=[(k,ctypes.c_int) for k in ('enabled','names','english','size','opacity','difficulty')]+[('mask',ctypes.c_uint),('selected',ctypes.c_int),('hidden',ctypes.c_int),('scope',ctypes.c_int),('icon_size',ctypes.c_int),('icon_opacity',ctypes.c_int),('item_names',ctypes.c_int),('legend',ctypes.c_int)]

class DrawOp(ctypes.Structure):
    _fields_=[(k,ctypes.c_float) for k in ('l','t','r','b')]+[('color',ctypes.c_uint),('glyph',ctypes.c_int)]

class ArrangeView(ctypes.Structure):
    _fields_=[('count',ctypes.c_uint),('rows',ctypes.c_char_p),('mismatches',ctypes.c_uint),('killed',ctypes.POINTER(ctypes.c_uint))]

class View(ctypes.Structure):
    _fields_=[(k,ctypes.c_float) for k in ('scale','ox','oy')]

class PlaceResult(ctypes.Structure):
    _fields_=[('place',ctypes.c_int),('placed',ctypes.c_int),('box',Box),('counts',ctypes.c_uint*7)]

class Core:
    def __init__(self,path=None):
        if path is None:
            path=Path(__file__).resolve().parents[1]/'local'/('libre0map.dylib' if sys.platform=='darwin' else 'libre0map.so')
        self.library=ctypes.CDLL(str(Path(path).resolve()))
        fn=self.library.re0_map_transform
        fn.argtypes=[ctypes.c_float,ctypes.c_float,ctypes.c_float,ctypes.POINTER(Transform)]
        fn.restype=ctypes.c_int
        quad=self.library.re0_sprite_quad
        quad.argtypes=[ctypes.c_float,ctypes.c_float,ctypes.c_uint,ctypes.c_int,
                       ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float)]
        quad.restype=ctypes.c_int
        uv=self.library.re0_sprite_uv
        uv.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_uint,ctypes.POINTER(ctypes.c_float)]
        uv.restype=ctypes.c_int

    def project(self,quad,viewport):
        if len(quad)!=16 or len(viewport)!=4: raise ValueError('quad/viewport shape')
        fn=self.library.re0_project_quad
        fn.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(Box)]
        fn.restype=ctypes.c_int
        out=Box()
        if not fn((ctypes.c_float*16)(*quad),(ctypes.c_float*4)(*viewport),ctypes.byref(out)): raise ValueError('invalid projection')
        return out.values()

    def default_settings(self):
        out=Settings();self.library.re0_settings_default(ctypes.byref(out));out.item_names=1;out.mask=127;return out # the game defaults item names off (H) and events off (spoilers); the checks exercise both, test_review42/51 check the real defaults; the checks exercise them, and test_review42 checks the real default

    def seen(self,rooms):
        """Per-piece arrays from {piece index: box}."""
        n=self.library.re0_frame_room_count();seen=(ctypes.c_ubyte*n)();boxes=(Box*n)()
        for i,b in rooms.items():seen[i]=1;boxes[i]=Box(*b)
        return seen,boxes

    def key(self,settings,key,rooms=None,flags=None):
        fn=self.library.re0_settings_key;fn.argtypes=[ctypes.POINTER(Settings),ctypes.c_int,ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_uint)];fn.restype=ctypes.c_int
        seen,_=self.seen(rooms or {})
        return fn(ctypes.byref(settings),ord(key),seen,(ctypes.c_uint*len(flags))(*flags) if flags else None)

    def room_state(self,index,flags):
        fn=self.library.re0_frame_room_state;fn.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];fn.restype=ctypes.c_int
        return fn(index,(ctypes.c_uint*len(flags))(*flags) if flags else None)

    def obstacle_fits(self,box):
        fn=self.library.re0_obstacle_fits;fn.argtypes=[Box];fn.restype=ctypes.c_int
        return bool(fn(Box(*box)))

    def frame(self,settings,width,height,rooms,obstacles=(),view=None,off=None,flags=None,arrange=None,map_area=None,display_mode=-1,gradients=None):
        """The op list the ASI paints for this state, and per-place placement results."""
        area=self.library.re0_display_bounds;area.argtypes=[Box,ctypes.c_int,Box,Box];area.restype=Box
        setter=self.library.re0_frame_set_map;setter.argtypes=[Box];setter(area(Box(*(map_area or (0,0,width,height))),display_mode,*(Box(*b) for b in (gradients or ((0,0,0,0),(0,0,0,0))))) if map_area is not None or display_mode!=-1 or gradients else Box(0,0,0,0))
        vp=self.library.re0_frame_set_viewport;vp.argtypes=[Box];shown=self.library.re0_display_area;shown.argtypes=[Box,ctypes.c_int];shown.restype=Box
        vp(shown(Box(*(map_area or (0,0,width,height))),display_mode) if map_area is not None or display_mode!=-1 or gradients else Box(0,0,0,0))
        fn=self.library.re0_frame_ops
        fn.argtypes=[ctypes.POINTER(Settings),ctypes.c_float,ctypes.c_float,ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(Box),ctypes.POINTER(Box),ctypes.c_uint,ctypes.POINTER(View),ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ArrangeView),ctypes.POINTER(DrawOp),ctypes.c_uint,ctypes.POINTER(PlaceResult),ctypes.POINTER(ctypes.c_uint)]
        fn.restype=ctypes.c_uint
        seen,boxes=self.seen(rooms);places=self.library.re0_frame_place_count()
        used=(Box*max(1,len(obstacles)))(*(Box(*b) for b in obstacles));ops=(DrawOp*8192)();results=(PlaceResult*places)();n=ctypes.c_uint()
        count=fn(ctypes.byref(settings),width,height,seen,boxes,used,len(obstacles),ctypes.byref(View(*view)) if view else None,(ctypes.c_ubyte*len(off))(*off) if off else None,(ctypes.c_uint*len(flags))(*flags) if flags else None,ctypes.byref(arrange) if arrange else None,ops,8192,results,ctypes.byref(n))
        return [dict(box=[o.l,o.t,o.r,o.b],color=o.color,glyph=o.glyph) for o in ops[:count]],[dict(place=r.place,box=r.box.values() if r.placed else None,counts=list(r.counts),result='placed' if r.placed else 'omitted-to-avoid-overlap-or-clip') for r in results[:n.value]]

    def layout_view(self,rooms):
        fn=self.library.re0_layout_view;fn.argtypes=[ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(Box),ctypes.POINTER(View)];fn.restype=ctypes.c_int
        seen,boxes=self.seen(rooms);out=View()
        return (out.scale,out.ox,out.oy) if fn(seen,boxes,ctypes.byref(out)) else None

    def marker_done(self,index,flags=None,arrange=None):
        fn=self.library.re0_frame_marker_done;fn.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ArrangeView)];fn.restype=ctypes.c_int
        return bool(fn(index,(ctypes.c_uint*len(flags))(*flags) if flags else None,ctypes.byref(arrange) if arrange else None))

    def condition_met(self,condition,flags=None):
        fn=self.library.re0_condition_met;fn.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];fn.restype=ctypes.c_int
        return bool(fn(condition,(ctypes.c_uint*len(flags))(*flags) if flags else None))

    def tally(self,rows,mode,mask,flags=None):
        fn=self.library.re0_content_tally
        fn.argtypes=[ctypes.POINTER(Content),ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ctypes.c_uint)]
        fn.restype=ctypes.c_uint
        counts=(ctypes.c_uint*7)()
        fn((Content*len(rows))(*(Content(*r) for r in rows)) if rows else None,len(rows),mode,mask,(ctypes.c_uint*len(flags))(*flags) if flags else None,counts)
        return list(counts)

    def place(self,room,width,height,clip,reserved):
        if len(room)!=4 or len(clip)!=4 or any(len(b)!=4 for b in reserved): raise ValueError('box shape')
        fn=self.library.re0_place_label
        fn.argtypes=[Box,ctypes.c_float,ctypes.c_float,Box,ctypes.POINTER(Box),ctypes.c_uint,ctypes.POINTER(Box)]
        fn.restype=ctypes.c_int
        out=Box();used=(Box*len(reserved))(*(Box(*b) for b in reserved))
        if not fn(Box(*room),width,height,Box(*clip),used,len(reserved),ctypes.byref(out)): return None
        return out.values()

    def transform(self,progress,focus):
        out=Transform()
        if not self.library.re0_map_transform(progress,*focus,ctypes.byref(out)):
            raise ValueError('invalid native map transform input')
        return out

    def quad(self,width,height,anchor,flip_y,matrix):
        if len(matrix)!=16:
            raise ValueError('sprite matrix must contain 16 floats')
        values=(ctypes.c_float*16)(*matrix)
        out=(ctypes.c_float*16)()
        if not self.library.re0_sprite_quad(width,height,anchor,flip_y,values,out):
            raise ValueError('invalid native sprite geometry')
        return list(out)

    def uv(self,rect,sampler):
        if len(rect)!=4:
            raise ValueError('sprite UV rectangle must contain four floats')
        values=(ctypes.c_float*4)(*rect)
        out=(ctypes.c_float*8)()
        if not self.library.re0_sprite_uv(values,sampler,out):
            raise ValueError('invalid native UV rectangle')
        return list(out)

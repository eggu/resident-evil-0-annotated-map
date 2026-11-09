/* Synthetic adapter test compiled as a separate DLL; never shipped as the ASI. */
#include "../src/runtime/re0_map.c"
static BYTE test_map[0x1270],test_state[0x100],test_instance[0x100],test_sprite[0x100],test_args[0x100];
static int calls[3];
static void put(BYTE *p,unsigned v){memcpy(p,&v,4);}
static void __thiscall stub_sprite(BYTE *self,BYTE *args){(void)self;(void)args;calls[2]++;}
static void __thiscall stub_instance(BYTE *self,BYTE *args){(void)self;calls[1]++;sprite_draw(test_sprite,0,args);}
static void __thiscall stub_map(BYTE *self,BYTE *args){(void)self;calls[0]++;instance_draw(test_instance,0,args);}
__declspec(dllexport) int re0_adapter_selftest(void) {
 tls=7;original_map=stub_map;original_instance=stub_instance;original_sprite=stub_sprite;
 put(test_map,0xcdc650);put(test_map+0x27c,3);put(test_map+0x278,(unsigned)(uintptr_t)test_state);
 put(test_state+0x44,0);put(test_instance+4,rooms[0].id);put(test_instance+0x6c,(unsigned)(uintptr_t)test_map);
 float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,100,80,0,1},wh[2]={40,20},view[4]={10,20,2,3};
 memcpy(test_sprite+0x10,matrix,64);memcpy(test_sprite+0xc0,wh,8);memcpy(test_args+0xb8,view,16);
 put(test_sprite+0xa0,0xff5);put(test_sprite+0xb0,0xffffffff);put(test_sprite+0xe4,1);
 map_draw(test_map,0,test_args);
 if(!pending.seen[0]||calls[0]!=1||calls[1]!=1||calls[2]!=1)return 1;
 RE0Box b=pending.room[0];
 if(b.l!=170||b.r!=250||b.t!=230||b.b!=290)return 2;
 if(TlsGetValue(tls)!=0)return 3;
 put(test_map+0x27c,4);map_draw(test_map,0,test_args);
 if(pending.seen[0]||pending.region!=-1||calls[2]!=2)return 4;
 put(test_map+0x27c,3);put(test_state+0x44,6);map_draw(test_map,0,test_args);
 if(pending.seen[0]||pending.region!=-1)return 5;
 put(test_state+0x44,0);put(test_instance+4,0xffffffff);map_draw(test_map,0,test_args);
 if(pending.seen[0]||pending.n_obstacles)return 6; /* 80px-wide background is not an icon obstacle */
 put(test_instance+4,rooms[0].id);put(test_sprite+0xb0,0);map_draw(test_map,0,test_args);
 if(pending.seen[0])return 7;
 put(test_sprite+0xb0,0xffffffff);put(test_sprite+0xe8,0x30);map_draw(test_map,0,test_args);
 if(!pending.seen[0])return 8; /* native alternate emit bits must not drop a room */
 return 0;
}
/* Icon texture path against a fake device: which texture and mip filter each op draws with, what each level receives. No D3D runtime, so no pixels. */
static int fake_fail_create,fake_fail_level=-1,fake_released,fake_mipfilter,fake_draws;static void *fake_bound,*fake_at_draw[4];static int fake_mip_at_draw[4];
static BYTE fake_store[4][256];static ULONG STDMETHODCALLTYPE fake_release(IDirect3DTexture9 *t){(void)t;fake_released++;return 0;}
static HRESULT STDMETHODCALLTYPE fake_lock(IDirect3DTexture9 *t,UINT l,D3DLOCKED_RECT *r,const RECT *a,DWORD f){(void)t;(void)a;(void)f;if((int)l==fake_fail_level)return E_FAIL;r->Pitch=64;r->pBits=fake_store[l];return 0;}
static HRESULT STDMETHODCALLTYPE fake_unlock(IDirect3DTexture9 *t,UINT l){(void)t;(void)l;return 0;}
static IDirect3DTexture9Vtbl fake_tex_v;static IDirect3DTexture9 fake_tex={&fake_tex_v};
static HRESULT STDMETHODCALLTYPE fake_create(IDirect3DDevice9 *d,UINT w,UINT h,UINT l,DWORD u,D3DFORMAT f,D3DPOOL p,IDirect3DTexture9 **o,HANDLE *s){(void)d;(void)w;(void)h;(void)l;(void)u;(void)f;(void)p;(void)s;if(fake_fail_create)return E_FAIL;*o=&fake_tex;return 0;}
static HRESULT STDMETHODCALLTYPE fake_set_tex(IDirect3DDevice9 *d,DWORD s,IDirect3DBaseTexture9 *t){(void)d;(void)s;fake_bound=t;return 0;}
static HRESULT STDMETHODCALLTYPE fake_sampler(IDirect3DDevice9 *d,DWORD s,D3DSAMPLERSTATETYPE k,DWORD v){(void)d;(void)s;if(k==D3DSAMP_MIPFILTER)fake_mipfilter=(int)v;return 0;}
static HRESULT STDMETHODCALLTYPE fake_draw(IDirect3DDevice9 *d,D3DPRIMITIVETYPE t,UINT n,const void *v,UINT st){(void)d;(void)t;(void)n;(void)v;(void)st;if(fake_draws<4){fake_at_draw[fake_draws]=fake_bound;fake_mip_at_draw[fake_draws]=fake_mipfilter;}fake_draws++;return 0;}
static IDirect3DDevice9Vtbl fake_dev_v;static IDirect3DDevice9 fake_dev={&fake_dev_v};
static void fake_init(void){fake_tex_v.Release=fake_release;fake_tex_v.LockRect=fake_lock;fake_tex_v.UnlockRect=fake_unlock;fake_dev_v.CreateTexture=fake_create;fake_dev_v.SetTexture=fake_set_tex;fake_dev_v.SetSamplerState=fake_sampler;fake_dev_v.DrawPrimitiveUP=fake_draw;}
/* 4x4, 3 levels: every level gets its own bytes. Returns 1 when all three arrive; on a failure the texture must be released and not handed out. */
__declspec(dllexport) int re0_probe_icon_upload(int fail_create,int fail_level) {
 static BYTE src[(16+4+1)*4];for(unsigned i=0;i<sizeof(src);i++)src[i]=(BYTE)(i<64?1:i<80?2:3);
 fake_init();fake_fail_create=fail_create;fake_fail_level=fail_level;fake_released=0;memset(fake_store,0,sizeof(fake_store));IDirect3DTexture9 *t=0;unsigned before=icon_load_failures;
 int ok=upload_mips(&fake_dev,src,4,4,3,&t);
 if(!ok)return (t?100:0)+(fake_released==(fail_create?0:1)?0:200)+(icon_load_failures==before+1?0:400);
 return 1+(fake_store[0][0]==1&&fake_store[0][64+15]==1?0:10)+(fake_store[1][0]==2?0:20)+(fake_store[2][0]==3?0:40);
}
/* Text, icon, text, icon: returns bound-texture and mip filter per draw as bits; icon_on picks the loaded or the failed case. */
__declspec(dllexport) unsigned re0_probe_icon_draw(int icon_on) {
 fake_init();static int a,i;atlas=(IDirect3DTexture9 *)&a;icon_tex=icon_on?(IDirect3DTexture9 *)&i:0;fake_draws=0;fake_bound=atlas;fake_mipfilter=D3DTEXF_NONE;icons_bound=0;icon_fallback_ops=0;
 RE0DrawOp t={0,0,10,10,0xffffffffu,0},ic={0,0,10,10,0xffffffffu,ICON_FIRST_GLYPH};
 draw_op(&fake_dev,&t);draw_op(&fake_dev,&ic);draw_op(&fake_dev,&t);draw_op(&fake_dev,&ic);
 unsigned r=0;for(int k=0;k<4;k++)r|=(unsigned)((fake_at_draw[k]==(void *)&i)|(fake_mip_at_draw[k]==D3DTEXF_LINEAR)<<1)<<(k*2);
 r|=icon_fallback_ops<<8;atlas=0;icon_tex=0;return r;
}
__declspec(dllexport) unsigned re0_probe_rows_format(void) {return (unsigned)rows_format();}
__declspec(dllexport) const char *re0_probe_rows_text(void) {return rows_text;}
__declspec(dllexport) int re0_probe_frame_shown(void) {return frame_shown();}
__declspec(dllexport) int re0_probe_frame_right(void) {return (int)frame_map.r;}
__declspec(dllexport) void re0_probe_frames(unsigned n) {present_count+=n;}
/* Native-dispatch harness: the real slot patching and the capture it produces. */
static Capture probe_capture;
__declspec(dllexport) int re0_probe_install(void) {tls=7;return patch_draw_slots();}
__declspec(dllexport) int re0_probe_install_all_scope(void) {return hook_all_scope();}
/* What the INI gives: scope, and the difficulty used while the table is unknown. */
__declspec(dllexport) int re0_probe_settings_load(void) {settings_load();return cfg.scope;}
__declspec(dllexport) int re0_probe_item_names(void) {settings_load();return cfg.item_names;}
__declspec(dllexport) int re0_probe_contents(void) {settings_load();return (int)cfg.mask;}
__declspec(dllexport) int re0_probe_color(int category) {settings_load();return (int)re0_frame_color((unsigned)category);}
static int probe_scope;
__declspec(dllexport) void re0_probe_set_scope(int scope) {cfg.scope=probe_scope=scope;}
__declspec(dllexport) const void *re0_probe_marker_def(unsigned index) {return &markers[index];}
__declspec(dllexport) const void *re0_probe_marker_state(unsigned index) {return &marker_state[index];}
__declspec(dllexport) const void *re0_probe_marker_rooms(void) {return marker_rooms;}
__declspec(dllexport) int re0_probe_room_state(unsigned index) {return re0_frame_room_state(index,live_flags);}

__declspec(dllexport) const void *re0_probe_room(unsigned index) {return index<ROOM_COUNT&&pending.seen[index]?&pending.room[index]:0;}
__declspec(dllexport) void re0_probe_read_flags(void) {read_flags();}
__declspec(dllexport) int re0_probe_difficulty(void) {read_arrange();return cfg.difficulty;}
__declspec(dllexport) int re0_probe_marker_done(unsigned index) {read_arrange();return re0_frame_marker_done(index,0,&live_arrange);}
__declspec(dllexport) void re0_probe_read_arrange(void) {read_arrange();}
__declspec(dllexport) const unsigned *re0_probe_killed(void) {return live_arrange.killed;}
/* The overlay's own frame call on given room boxes; flags come from read_flags. */
static RE0DrawOp probe_ops[OVERLAY_OPS];
__declspec(dllexport) void *re0_probe_ops(void) {return probe_ops;}
__declspec(dllexport) void re0_probe_room_box(unsigned index,const float *box) {probe_capture.seen[index]=1;memcpy(&probe_capture.room[index],box,sizeof(RE0Box));}
__declspec(dllexport) void re0_probe_rooms_clear(void) {memset(&probe_capture,0,sizeof(probe_capture));}
__declspec(dllexport) unsigned re0_probe_overlay(unsigned width,unsigned height) {re0_settings_default(&cfg);cfg.scope=probe_scope;cfg.item_names=1;cfg.mask=RE0_MASK_ALL; /* the gates check names and events; the game defaults are item names off and events off */return overlay_ops(&probe_capture,width,height,probe_ops);}
__declspec(dllexport) int re0_probe_screen_clear(void) {return screen_clear();}
__declspec(dllexport) int re0_probe_gate(unsigned generation,unsigned map) {Capture c={0};c.map=(BYTE *)(uintptr_t)map;c.generation=generation;return overlay_allowed(&c,screen_clear());}
__declspec(dllexport) int re0_probe_condition(unsigned condition) {return re0_condition_met(condition,live_flags);}
__declspec(dllexport) unsigned re0_probe_counter(unsigned index) {
 const unsigned *c=&diag.maps;return index<24?c[index]:0;
}
__declspec(dllexport) unsigned re0_probe_room_index(unsigned region,unsigned id) {
 for(unsigned i=0;i<ROOM_COUNT;i++)if(rooms[i].region==region&&rooms[i].id==id)return i;
 return 0xffffffff;
}

__declspec(dllexport) int re0_probe_display_mode(void){return display_mode();}
__declspec(dllexport) const RE0Box *re0_probe_display_bounds(unsigned w,unsigned h){static RE0Box b;overlay_ops(&pending,w,h,probe_ops);b=re0_frame_map();return &b;}

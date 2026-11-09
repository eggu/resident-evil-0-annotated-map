/* RE0 2025-only experimental native-draw annotation adapter. */
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include "../core/frame.h"
#include "labels_generated.h"
static float lower(float a,float b){return a<b?a:b;}
static float upper(float a,float b){return a>b?a:b;}
#define VA(a) ((BYTE *)(uintptr_t)(a))
#define MAX_OBSTACLES 256
static const char capture_profile[]="67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b";
static CRITICAL_SECTION lock;
static DWORD tls;
static char ini_path[MAX_PATH],atlas_path[MAX_PATH],icon_path[MAX_PATH],log_path[MAX_PATH],report_path[MAX_PATH];
static RE0Settings cfg={1,1,0,100,60,1,RE0_MASK_DEFAULT,-1,0,RE0_SCOPE_VISITED,100,80,0,1};
/* Difficulty when the table is unknown (random modes): the INI's value, kept silently; it has no key. */
static int ini_difficulty=1;
static HANDLE logfile=INVALID_HANDLE_VALUE;
static IDirect3DTexture9 *atlas,*icon_tex;
static IDirect3DDevice9 *icon_device;
static unsigned icon_load_failures,icon_fallback_ops;
static IDirect3DDevice9 *atlas_device;
static DWORD draws;
static BYTE *image;
typedef void (__thiscall *GuiDraw)(BYTE *,BYTE *);
static GuiDraw original_map,original_instance,original_sprite;
typedef struct {
 BYTE *map; int region,current; unsigned generation;
 RE0Box room[ROOM_COUNT],obstacles[MAX_OBSTACLES];
 unsigned char seen[ROOM_COUNT]; unsigned n_obstacles; DWORD tick;
 float zoom_t,pan_x,pan_y; int zoom_mode,panning;
 RE0Box area; int display_mode;
} Capture;
static Capture pending;
static RE0GameRect game_rect(const BYTE *args);
static int display_mode(void);
static unsigned next_generation;
typedef HRESULT (WINAPI *PresentFn)(IDirect3DDevice9 *,const RECT *,const RECT *,HWND,const RGNDATA *);
static struct {void **volatile vtable; PresentFn volatile present; int warned; } chains[8];
/* Live-test counters: the log says which step dropped room data, so one run identifies the cause. */
static struct {
 unsigned maps,maps_closed,maps_empty,instances,no_context,owner_miss,id_miss,id_hit,sprites,sprite_no_context,
  sprite_unreadable,sprite_no_texture,sprite_alt_mode,sprite_transparent,sprite_bad_quad,sprite_room,sprite_other,flags_unreadable,layout_rejected,fade_unreadable,arrange_unreadable,arrange_mismatch,actors_unreadable,actors_overflow,rect_unreadable;
 unsigned sample_instance[3],sample_map,sample_sprite[5];float sample_size[2];DWORD map_thread;
} diag;
static int readable(const void *ptr,size_t size) {
 uintptr_t p=(uintptr_t)ptr,end=p+size; MEMORY_BASIC_INFORMATION m;
 if(!p||end<p) return 0;
 while(p<end) {
  if(!VirtualQuery((void *)p,&m,sizeof(m))||m.State!=MEM_COMMIT||m.Protect&(PAGE_GUARD|PAGE_NOACCESS)) return 0;
  uintptr_t next=(uintptr_t)m.BaseAddress+m.RegionSize;
  if(next<=p) return 0; p=next;
 }
 return 1;
}
static int executable(const void *ptr) {
 MEMORY_BASIC_INFORMATION m;
 return VirtualQuery(ptr,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&
        (m.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY));
}
static unsigned u32(const void *p) {unsigned v;memcpy(&v,p,4);return v;}
static void log_line(const char *text) {
 if(logfile==INVALID_HANDLE_VALUE)return;
 char stamp[24];DWORD n;int len=snprintf(stamp,sizeof(stamp),"[%6lu] ",GetTickCount()/1000%1000000);
 WriteFile(logfile,stamp,(DWORD)len,&n,0);WriteFile(logfile,text,(DWORD)strlen(text),&n,0);
}
/* F8 records every sprite the game draws in one frame, in draw order: the reference the emulator must reproduce.
 * GUI objects and their texture resources only; nothing from saves. */
#define DUMP_SPRITES 1536
#define DUMP_SPRITE_BYTES 0x110
#define DUMP_TEXTURES 64
#define DUMP_RESOURCE_BYTES 0x80
typedef struct {BYTE sprite[DUMP_SPRITE_BYTES];float view[4];unsigned texture;int room,instance_id;} DumpRow;
static struct {volatile LONG state;unsigned count,textures;DumpRow *rows;unsigned texture_ptr[DUMP_TEXTURES];BYTE texture_head[DUMP_TEXTURES][DUMP_RESOURCE_BYTES];unsigned region;} dump;
static size_t put_hex(char *out,const BYTE *data,unsigned n){static const char h[]="0123456789abcdef";for(unsigned i=0;i<n;i++){out[i*2]=h[data[i]>>4];out[i*2+1]=h[data[i]&15];}return n*2u;}
static void dump_write(void) {
 const size_t cap=(size_t)dump.count*(DUMP_SPRITE_BYTES*2+160)+DUMP_TEXTURES*(DUMP_RESOURCE_BYTES*2+64)+1024;
 char *body=HeapAlloc(GetProcessHeap(),0,cap);if(!body)return;
 char tmp[MAX_PATH],path[MAX_PATH];size_t at=0;
 snprintf(path,sizeof(path),"%s",report_path);char *dot=strrchr(path,'-');if(!dot){HeapFree(GetProcessHeap(),0,body);return;}strcpy(dot,"-sprites.json");
 at+=(size_t)snprintf(body+at,cap-at,"{\"schema_version\":2,\"evidence\":\"captured-native-sprites\",\"profile_sha256\":\"%s\",\"region\":%d,\"textures\":[",capture_profile,(int)dump.region);
 for(unsigned t=0;t<dump.textures;t++){at+=(size_t)snprintf(body+at,cap-at,"%s{\"ptr\":%u,\"head\":\"",t?",":"",dump.texture_ptr[t]);at+=put_hex(body+at,dump.texture_head[t],DUMP_RESOURCE_BYTES);body[at++]='"';body[at++]='}';}
 at+=(size_t)snprintf(body+at,cap-at,"],\"sprites\":[");
 for(unsigned n=0;n<dump.count;n++){const DumpRow *r=&dump.rows[n];
  at+=(size_t)snprintf(body+at,cap-at,"%s{\"texture\":%u,\"room\":%d,\"instance\":%d,\"view\":[%.4f,%.4f,%.6f,%.6f],\"bytes\":\"",n?",":"",r->texture,r->room,r->instance_id,(double)r->view[0],(double)r->view[1],(double)r->view[2],(double)r->view[3]);
  at+=put_hex(body+at,r->sprite,DUMP_SPRITE_BYTES);body[at++]='"';body[at++]='}';}
 at+=(size_t)snprintf(body+at,cap-at,"]}\n");
 if(snprintf(tmp,sizeof(tmp),"%s.tmp",path)<(int)sizeof(tmp)) {
  HANDLE f=CreateFileA(tmp,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);
  if(f!=INVALID_HANDLE_VALUE) {
   DWORD n;int ok=WriteFile(f,body,(DWORD)at,&n,0)&&n==at&&FlushFileBuffers(f);CloseHandle(f);
   if(ok&&MoveFileExA(tmp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){char text[96];snprintf(text,sizeof(text),"Sprite dump saved: %u sprites, %u textures\r\n",dump.count,dump.textures);log_line(text);}
  }
 }
 HeapFree(GetProcessHeap(),0,body);
}
static void dump_sprite(BYTE *self,BYTE *args,int room,int instance_id) {
 if(dump.state!=2||!dump.rows||dump.count>=DUMP_SPRITES||!readable(self,DUMP_SPRITE_BYTES)||!readable(args,0xc8))return;
 DumpRow *r=&dump.rows[dump.count++];memcpy(r->sprite,self,DUMP_SPRITE_BYTES);memcpy(r->view,args+0xb8,16);r->room=room;r->instance_id=instance_id;
 r->texture=u32(self+0xe4);
 unsigned t;for(t=0;t<dump.textures&&dump.texture_ptr[t]!=r->texture;t++);
 if(t==dump.textures&&t<DUMP_TEXTURES&&r->texture&&readable((void *)(uintptr_t)r->texture,DUMP_RESOURCE_BYTES)){dump.texture_ptr[t]=r->texture;memcpy(dump.texture_head[t],(void *)(uintptr_t)r->texture,DUMP_RESOURCE_BYTES);dump.textures++;}
}
/* Called once per Present: 1 armed by F8 -> 2 records the next whole frame -> written at the following Present. */
static void dump_step(int region) {
 if(dump.state==1){if(!dump.rows)dump.rows=HeapAlloc(GetProcessHeap(),0,sizeof(DumpRow)*DUMP_SPRITES);dump.count=0;dump.textures=0;dump.region=(unsigned)region;InterlockedExchange(&dump.state,dump.rows?2:0);}
 else if(dump.state==2){InterlockedExchange(&dump.state,0);dump_write();}
}
static void diag_report(const char *why) {
 char text[720];
 snprintf(text,sizeof(text),"Diag %s: map=%u closed=%u empty=%u | inst=%u noctx=%u owner_miss=%u id_miss=%u id_hit=%u | sprite=%u noctx=%u unread=%u notex=%u altmode=%u clear=%u badquad=%u room=%u other=%u flagsbad=%u layoutbad=%u fadebad=%u arrangebad=%u rowbad=%u actorsbad=%u actorslong=%u rectbad=%u | map@%08x inst vt=%08x id=%u owner=%08x | sprite e4=%08x e8=%08x f54=%08x a0=%u b0=%08x size=%.1fx%.1f\r\n",
  why,diag.maps,diag.maps_closed,diag.maps_empty,diag.instances,diag.no_context,diag.owner_miss,diag.id_miss,diag.id_hit,diag.sprites,diag.sprite_no_context,diag.sprite_unreadable,diag.sprite_no_texture,diag.sprite_alt_mode,diag.sprite_transparent,diag.sprite_bad_quad,diag.sprite_room,diag.sprite_other,diag.flags_unreadable,diag.layout_rejected,diag.fade_unreadable,diag.arrange_unreadable,diag.arrange_mismatch,diag.actors_unreadable,diag.actors_overflow,diag.rect_unreadable,
  diag.sample_map,diag.sample_instance[0],diag.sample_instance[1],diag.sample_instance[2],diag.sample_sprite[0],diag.sample_sprite[1],diag.sample_sprite[2],diag.sample_sprite[3],diag.sample_sprite[4],(double)diag.sample_size[0],(double)diag.sample_size[1]);
 log_line(text);
}
static int in_range(int v,int lo,int hi) {return v<lo?lo:v>hi?hi:v;}
static int module_path(char *out,const char *name) {
 DWORD n=GetModuleFileNameA((HMODULE)image,out,MAX_PATH);
 if(!n||n>=MAX_PATH) return 0;
 char *slash=strrchr(out,'\\');if(!slash||(size_t)(slash-out)+1+strlen(name)>=MAX_PATH) return 0;
 strcpy(slash+1,name);return 1;
}
static int supported_exe(void) {return (uintptr_t)GetModuleHandleA(0)==0x400000;}
static int settings_migrated; /* the INI came from before Version 50: sizes (before 44) were converted, ItemNames moved to the 3-state value and Contents gained the event bit; the file is rewritten once the log is open */
/* [Colors]: one #RRGGBB per category, keys in category id order. A missing or malformed value keeps the shipped colour. */
static const char *const color_keys[RE0_CATEGORIES]={"Lock","KeyItem","File","Puzzle","Item","Enemy","Event"};
static void colors_load(void) {
 re0_frame_reset_colors();
 for(unsigned i=0;i<RE0_CATEGORIES;i++){char text[32];unsigned rgb;GetPrivateProfileStringA("Colors",color_keys[i],"",text,sizeof(text),ini_path);if(re0_color_parse(text,&rgb))re0_frame_set_color(i,rgb);else if(text[0])log_line("Colors: unreadable value ignored\r\n");}
}
static void settings_load(void) {
 cfg.enabled=!!GetPrivateProfileIntA("Map","Enabled",1,ini_path);
 cfg.english=!!GetPrivateProfileIntA("Map","English",0,ini_path);
 cfg.names=!!GetPrivateProfileIntA("Map","Names",1,ini_path);
 cfg.opacity=in_range((int)GetPrivateProfileIntA("Map","NameOpacity",60,ini_path),10,100);
 ini_difficulty=cfg.difficulty=in_range((int)GetPrivateProfileIntA("Map","Difficulty",1,ini_path),0,2);
 /* RE1 HD's name and values: 0 visited, 1 revealed, 2 all. */
 cfg.scope=(int)GetPrivateProfileIntA("Map","Visibility",RE0_SCOPE_VISITED,ini_path);if(cfg.scope<RE0_SCOPE_VISITED||cfg.scope>RE0_SCOPE_ALL)cfg.scope=RE0_SCOPE_VISITED;
 cfg.icon_opacity=in_range((int)GetPrivateProfileIntA("Map","IconOpacity",80,ini_path),10,100);
 cfg.legend=!!GetPrivateProfileIntA("Map","Legend",1,ini_path);
 const int version=(int)GetPrivateProfileIntA("Map","Version",0,ini_path);
 cfg.mask=re0_settings_contents(version,(int)GetPrivateProfileIntA("Map","Contents",(int)RE0_MASK_DEFAULT,ini_path));
 cfg.item_names=re0_settings_item_names(version,(int)GetPrivateProfileIntA("Map","ItemNames",0,ini_path));
 colors_load();
 settings_migrated=re0_settings_ini_sizes(&cfg,version,(int)GetPrivateProfileIntA("Map","NameSize",(UINT)-1,ini_path),(int)GetPrivateProfileIntA("Map","IconSize",(UINT)-1,ini_path));
}
/* The INI is edited in place (re0_ini_merge): the user's [Colors], comments and key order survive a save. */
static void settings_save(void) {
 char tmp[MAX_PATH];
 if(snprintf(tmp,sizeof(tmp),"%s.tmp",ini_path)>=(int)sizeof(tmp))return;
 static char old[16384],out[32768];DWORD got=0;
 HANDLE in=CreateFileA(ini_path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,0,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,0);
 if(in!=INVALID_HANDLE_VALUE){if(!ReadFile(in,old,sizeof(old),&got,0))got=0;CloseHandle(in);}
 if(got==sizeof(old)){log_line("Settings save skipped: INI too large to edit\r\n");return;}
 static const char *const keys[13]={"Version","Legend","IconSize","IconOpacity","ItemNames","Enabled","English","Names","NameSize","NameOpacity","Difficulty","Visibility","Contents"};
 const int numbers[13]={RE0_SETTINGS_VERSION,cfg.legend,cfg.icon_size,cfg.icon_opacity,cfg.item_names,cfg.enabled,cfg.english,cfg.names,cfg.size,cfg.opacity,ini_difficulty,cfg.scope,(int)cfg.mask};
 char text[13][16];const char *values[13];
 for(unsigned i=0;i<13;i++){snprintf(text[i],sizeof(text[i]),"%d",numbers[i]);values[i]=text[i];}
 char tail[512];int at=snprintf(tail,sizeof(tail),"\r\n[Colors]\r\n; #RRGGBB per category\r\n");
 for(unsigned i=0;i<RE0_CATEGORIES&&at>0&&at<(int)sizeof(tail);i++)at+=snprintf(tail+at,sizeof(tail)-(size_t)at,"%s=#%06X\r\n",color_keys[i],re0_frame_color(i));
 const unsigned len=re0_ini_merge(old,got,keys,values,13,tail,out,sizeof(out));
 if(!len){log_line("Settings save failed: INI did not fit\r\n");return;}
 HANDLE f=CreateFileA(tmp,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);
 if(f==INVALID_HANDLE_VALUE){log_line("Settings open failed\r\n");return;}
 DWORD n;int ok=WriteFile(f,out,len,&n,0)&&n==len&&FlushFileBuffers(f);CloseHandle(f);
 if(!ok||!MoveFileExA(tmp,ini_path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))log_line("Settings save failed; previous INI retained\r\n");
}
/* Diagnostic label only: a stray value from another draw thread costs one wrong tag in a dump. */
static volatile int dump_instance=-1;
static void __fastcall map_draw(BYTE *self,void *unused,BYTE *args) {
 (void)unused; Capture *previous=TlsGetValue(tls);
 Capture c={0};c.display_mode=display_mode();const RE0GameRect rect=game_rect(args);c.area=re0_map_viewport(&rect);c.map=self;c.region=-1;c.current=-1;c.tick=GetTickCount();
 if(readable(self,0x280)&&u32(self)==0xcdc650&&u32(self+0x27c)==3) {
  BYTE *state=(BYTE *)(uintptr_t)u32(self+0x278);
  if(readable(state,0x48)&&u32(state+0x44)<6)c.region=(int)u32(state+0x44);
  if(readable(state,0x70)) {
   float p[5];memcpy(&p[0],state+0x54,4);memcpy(&p[1],state+0x5c,16);
   c.zoom_t=p[0];c.pan_x=p[1];c.pan_y=p[2];c.zoom_mode=(int)u32(state+0x58);c.panning=p[1]!=p[3]||p[2]!=p[4];
  } else c.zoom_mode=-1;
 }
 diag.maps++;diag.sample_map=(unsigned)(uintptr_t)self;if(c.region<0)diag.maps_closed++;
 TlsSetValue(tls,&c);
 original_map(self,args);
 TlsSetValue(tls,previous);
 int data=c.n_obstacles>0;
 for(unsigned i=0;i<ROOM_COUNT&&!data;i++)data=c.seen[i];
 if(!data&&c.region>=0)diag.maps_empty++;
 EnterCriticalSection(&lock);
 /* Several uGUIMap objects can draw in one frame: an empty one must not hide the one with rooms. */
 if(data||c.tick-pending.tick>100||(!pending.n_obstacles&&pending.region<0)){c.generation=++next_generation;pending=c;}
 LeaveCriticalSection(&lock);
}
static void __fastcall instance_draw(BYTE *self,void *unused,BYTE *args) {
 (void)unused;Capture *c=TlsGetValue(tls);int old=-1;
 diag.instances++;
 const int outer_instance=dump_instance;if(readable(self,8))dump_instance=(int)u32(self+4);
 if(!c)diag.no_context++;
 else {
  old=c->current;c->current=-1;
  if(c->region>=0&&readable(self,0x70)) {
   unsigned id=u32(self+4),owner=u32(self+0x6c);
   if(!diag.sample_instance[0]){diag.sample_instance[0]=u32(self);diag.sample_instance[1]=id;diag.sample_instance[2]=owner;}
   if(owner!=(unsigned)(uintptr_t)c->map)diag.owner_miss++;
   else {
    for(unsigned i=0;i<ROOM_COUNT;i++)if(rooms[i].region==(unsigned)c->region&&rooms[i].id==id){c->current=(int)i;break;}
    if(c->current<0)diag.id_miss++;else diag.id_hit++;
   }
  }
 }
 original_instance(self,args);
 if(c)c->current=old;
 dump_instance=outer_instance;
}
static int display_mode(void){const BYTE *p=(const BYTE *)(uintptr_t)u32(VA(0xdcc06c));return p&&readable(p,0x24)?(int)u32(p+0x20):-1;}
/* Unreadable means the plain case, target = back buffer: counted, and the log line shows what a wrong overlay had to work with. */
static RE0GameRect game_rect(const BYTE *args) {
 RE0GameRect g={0};
 const BYTE *r=(const BYTE *)(uintptr_t)u32(args+4),*s=r&&readable(VA(0xe2d40c),4)?(const BYTE *)(uintptr_t)u32(VA(0xe2d40c)):0;
 if(!r||!s||!readable(r,0x100)||!readable(s,0xc0)||!readable(s+0x433e50,8)){diag.rect_unreadable++;return g;}
 g=(RE0GameRect){(int)u32(r+0xbc),(int)u32(r+0xc0),(int)(u32(r+0xfc)&0xffff),(int)(u32(r+0xfc)>>16),(int)u32(s+0xb8),(int)u32(s+0xbc),(int)u32(s+0xa4),(int)u32(s+0xa8),(int)u32(s+0xac),(int)u32(s+0xb0),(int)u32(s+0x433e50),(int)u32(s+0x433e54),(int)u32(r+0xc4),(int)u32(r+0xc8)};
 static RE0GameRect logged;static unsigned changes;
 if((g.view_l!=logged.view_l||g.target_w!=logged.target_w||g.render_w!=logged.render_w||g.blit_l!=logged.blit_l||g.back_w!=logged.back_w)&&changes<8&&logfile!=INVALID_HANDLE_VALUE){char text[160];logged=g;changes++;snprintf(text,sizeof(text),"Game rect view=%d,%d target=%dx%d render=%dx%d blit=%d,%d,%d,%d back=%dx%d\r\n",g.view_l,g.view_t,g.target_w,g.target_h,g.render_w,g.render_h,g.blit_l,g.blit_t,g.blit_r,g.blit_b,g.back_w,g.back_h);log_line(text);}
 return g;
}
/* V hides the frame by not drawing its sprites. The help panel's 176x152 is drawn only when it shows (frame on 39 sprites, off 25, live 2560x1440), and only in that state. */
static unsigned present_count,frame_seen_at,list_seen_at;static int frame_seen,list_seen;static RE0Box frame_map;
static RE0Box gradient[2];static unsigned gradient_at[2];static int gradient_seen[2];
static int frame_shown(void){return frame_seen&&present_count-frame_seen_at<=2?(list_seen&&present_count-list_seen_at<=2?2:1):0;}
static void __fastcall sprite_draw(BYTE *self,void *unused,BYTE *args) {
 (void)unused;
 original_sprite(self,args);
 if(readable(self,0xf0)&&readable(args,0xc8)&&u32(self+0xb0)>>24) {
  float dim[2];memcpy(dim,self+0xc0,8);
  /* map_bg01.gui has two 224x720 sprites. Use their native transformed quads, including Original mode and animation. */
  if(dim[0]==224.0f&&dim[1]==720.0f) {
   float m[16],v[4];RE0SpriteQuad q;RE0Box b;memcpy(m,self+0x10,64);memcpy(v,args+0xb8,16);
   if(re0_sprite_quad(dim[0],dim[1],u32(self+0xa0),!!(u32(self+0x54)&(1u<<22)),m,&q)&&re0_project_quad(&q,v,&b)) {
    const RE0GameRect r=game_rect(args);b=re0_gui_to_backbuffer(b,&r);const RE0Box a=re0_map_viewport(&r);
    const unsigned side=(b.l+b.r>a.l+a.r);gradient[side]=b;gradient_at[side]=present_count;gradient_seen[side]=1;
   } else diag.sprite_bad_quad++;
  }
  /* The item list strip, 744x93, is drawn only while the list is open (76-sprite dump, 39 without). */
  if(dim[0]==744.0f&&dim[1]==93.0f){list_seen=1;list_seen_at=present_count;}
  if(dim[0]==176.0f&&dim[1]==152.0f) {
   const RE0GameRect rect=game_rect(args);float scale[6];memcpy(scale,self+0x10,sizeof(scale)); /* the sprite's matrix: GUI units to target pixels, 2 at 2560x1440 */
   frame_map=re0_gui_to_backbuffer((RE0Box){0,0,1280*scale[0],720*scale[5]},&rect);frame_seen=1;frame_seen_at=present_count;
  }
 }
 diag.sprites++;
 Capture *c=TlsGetValue(tls);
 dump_sprite(self,args,c?c->current:-1,dump_instance);
 if(!c){diag.sprite_no_context++;return;}
 if(c->region<0)return;
 if(!readable(self,0xf0)||!readable(args,0xc8)){diag.sprite_unreadable++;return;}
 unsigned flags=u32(self+0x54),alpha=u32(self+0xb0)>>24;
 if(!diag.sample_sprite[0]){diag.sample_sprite[0]=u32(self+0xe4);diag.sample_sprite[1]=u32(self+0xe8);diag.sample_sprite[2]=flags;diag.sample_sprite[3]=u32(self+0xa0);diag.sample_sprite[4]=u32(self+0xb0);memcpy(diag.sample_size,self+0xc0,8);}
 if(!u32(self+0xe4)){diag.sprite_no_texture++;return;}
 /* 0x890b5d only picks a native emit branch on these bits; geometry is still the same rectangle. */
 if(u32(self+0xe8)&0x30)diag.sprite_alt_mode++;
 if(!alpha){diag.sprite_transparent++;return;}
 float matrix[16],dimensions[2],view[4];RE0SpriteQuad quad;RE0Box box;
 memcpy(matrix,self+0x10,sizeof(matrix));memcpy(dimensions,self+0xc0,8);memcpy(view,args+0xb8,16);
 if(!re0_sprite_quad(dimensions[0],dimensions[1],u32(self+0xa0),!!(flags&(1u<<22)),matrix,&quad)||!re0_project_quad(&quad,view,&box)){diag.sprite_bad_quad++;return;}
 {const RE0GameRect rect=game_rect(args);box=re0_gui_to_backbuffer(box,&rect);}
 if(c->current>=0) {
  unsigned i=(unsigned)c->current;
  if(!c->seen[i])c->room[i]=box;
  else {RE0Box *b=&c->room[i];b->l=lower(b->l,box.l);b->t=lower(b->t,box.t);b->r=upper(b->r,box.r);b->b=upper(b->b,box.b);}
  c->seen[i]=1;diag.sprite_room++;
 } else {diag.sprite_other++;if(c->n_obstacles<MAX_OBSTACLES&&re0_obstacle_fits(box))c->obstacles[c->n_obstacles++]=box;}
}
/* levels BGRA levels, largest first, tightly packed. A failure of any level releases the texture: icon ops then draw plain squares, so a mark is still seen. */
static int upload_mips(IDirect3DDevice9 *dev,const BYTE *src,unsigned w,unsigned h,unsigned levels,IDirect3DTexture9 **out) {
 IDirect3DTexture9 *t=0;
 if(FAILED(IDirect3DDevice9_CreateTexture(dev,w,h,levels,0,D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&t,0))||!t){icon_load_failures++;return 0;}
 for(unsigned l=0;l<levels;l++) {
  D3DLOCKED_RECT rect;
  if(FAILED(IDirect3DTexture9_LockRect(t,l,&rect,0,0))){icon_load_failures++;IDirect3DTexture9_Release(t);return 0;}
  for(unsigned y=0;y<h;y++)memcpy((BYTE *)rect.pBits+y*rect.Pitch,src+y*w*4,w*4);
  IDirect3DTexture9_UnlockRect(t,l);
  src+=w*h*4;
  w=w>1?w/2:1;h=h>1?h/2:1;
 }
 *out=t;return 1;
}
static void load_icons(IDirect3DDevice9 *dev) {
 if(icon_device==dev)return; /* once per device: a failure is not retried every frame */
 if(icon_tex){IDirect3DTexture9_Release(icon_tex);icon_tex=0;}icon_device=dev;
 HANDLE f=CreateFileA(icon_path,GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,0);int ok=f!=INVALID_HANDLE_VALUE;BYTE *buf=0;
 if(ok) {
  DWORD n=0;ok=GetFileSize(f,0)==ICON_BYTES&&(buf=HeapAlloc(GetProcessHeap(),0,ICON_BYTES))!=0&&ReadFile(f,buf,ICON_BYTES,&n,0)&&n==ICON_BYTES;CloseHandle(f);
  if(!ok)icon_load_failures++;
 } else icon_load_failures++;
 if(ok)ok=upload_mips(dev,buf,ICON_TEX,ICON_TEX_H,ICON_LEVELS,&icon_tex);
 if(buf)HeapFree(GetProcessHeap(),0,buf);
 if(!ok)log_line("Icon texture missing, invalid, or creation failed; marks drawn as plain squares\r\n");
}
static int load_atlas(IDirect3DDevice9 *dev) {
 if(atlas_device==dev&&atlas)return 1;
 if(atlas){IDirect3DTexture9_Release(atlas);atlas=0;}atlas_device=dev;
 HANDLE f=CreateFileA(atlas_path,GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,0);
 if(f==INVALID_HANDLE_VALUE)return 0;
 DWORD expected=ATLAS_W*ATLAS_H*4;
 if(GetFileSize(f,0)!=expected){CloseHandle(f);return 0;}
 BYTE *buf=HeapAlloc(GetProcessHeap(),0,expected);DWORD n=0;int ok=buf&&ReadFile(f,buf,expected,&n,0)&&n==expected;CloseHandle(f);
 if(ok)ok=SUCCEEDED(IDirect3DDevice9_CreateTexture(dev,ATLAS_W,ATLAS_H,1,0,D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&atlas,0));
 if(ok) {
  D3DLOCKED_RECT rect;ok=SUCCEEDED(IDirect3DTexture9_LockRect(atlas,0,&rect,0,0));
  if(ok){for(unsigned y=0;y<ATLAS_H;y++)memcpy((BYTE *)rect.pBits+y*rect.Pitch,buf+y*ATLAS_W*4,ATLAS_W*4);IDirect3DTexture9_UnlockRect(atlas,0);}
 }
 if(buf)HeapFree(GetProcessHeap(),0,buf);
 if(!ok&&atlas){IDirect3DTexture9_Release(atlas);atlas=0;}return ok;
}
typedef struct {float x,y,z,rhw;DWORD color;float u,v;} Vertex;
static void draw_tile(IDirect3DDevice9 *dev,const Glyph *g,RE0Box b,DWORD color,float tw,float th) {
 float l=b.l-.5f,t=b.t-.5f,r=b.r-.5f,bt=b.b-.5f;
 float u=(float)g->x/tw,v=(float)g->y/th,u2=(float)(g->x+g->w)/tw,v2=(float)(g->y+g->h)/th;
 Vertex q[6]={{l,t,0,1,color,u,v},{r,t,0,1,color,u2,v},{l,bt,0,1,color,u,v2},{l,bt,0,1,color,u,v2},{r,t,0,1,color,u2,v},{r,bt,0,1,color,u2,v2}};
 IDirect3DDevice9_DrawPrimitiveUP(dev,D3DPT_TRIANGLELIST,2,q,sizeof(Vertex));
}
static int icons_bound;
static void bind_icons(IDirect3DDevice9 *dev,int on) {
 if(icons_bound==on)return;
 icons_bound=on;
 IDirect3DDevice9_SetTexture(dev,0,on?(IDirect3DBaseTexture9 *)icon_tex:(IDirect3DBaseTexture9 *)atlas);
 IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MIPFILTER,on?D3DTEXF_LINEAR:D3DTEXF_NONE);
}
static void draw_op(IDirect3DDevice9 *dev,const RE0DrawOp *op) {
 RE0Box b={op->l,op->t,op->r,op->b};
 /* Solid fills sample well inside the white block so bilinear filtering cannot reach its edge. */
 Glyph inner={(unsigned short)(solid_glyph.x+2),(unsigned short)(solid_glyph.y+2),(unsigned short)(solid_glyph.w-4),(unsigned short)(solid_glyph.h-4)};
 if(op->glyph>=ICON_FIRST_GLYPH&&icon_tex){bind_icons(dev,1);draw_tile(dev,&glyphs[op->glyph],b,op->color,ICON_TEX,ICON_TEX_H);return;}
 bind_icons(dev,0);
 if(op->glyph>=ICON_FIRST_GLYPH){icon_fallback_ops++;draw_tile(dev,&inner,b,0xffa0a0a0u,ATLAS_W,ATLAS_H);return;}
 draw_tile(dev,op->glyph<0?&inner:&glyphs[op->glyph],b,op->color,ATLAS_W,ATLAS_H);
}
/* Live log showed one F8 press firing three times 200 ms apart, so a toggle needs a rest period too. */
static int edge(int vk) {
 static BYTE down[256];static DWORD last[256];
 int now=!!(GetAsyncKeyState(vk)&0x8000),hit=now&&!down[vk];down[vk]=(BYTE)now;
 if(!hit)return 0;
 DWORD tick=GetTickCount();if(tick-last[vk]<350)return 0;
 last[vk]=tick;return 1;
}
/* The array the game's own spawn gate tests. Unreadable means unknown: all zero, so conditional rows stay off rather than appear falsely. */
static unsigned live_flags[RE0_FLAG_WORDS];
static void read_flags(void) {
 BYTE *owner=(BYTE *)(uintptr_t)u32(VA(0xdcc014));
 if(owner&&readable(owner+0x20,sizeof(live_flags))){memcpy(live_flags,owner+0x20,sizeof(live_flags));return;}
 memset(live_flags,0,sizeof(live_flags));
 if(!diag.flags_unreadable++)log_line("Game flags unreadable; conditional rows and rooms by scope hidden\r\n");
}
/* Placement manager: which table rows are taken. Unreadable means unknown, so nothing is treated as taken. */
static RE0ArrangeView live_arrange;static int live_table_mode=-1;
/* A kill in a loaded room reaches its row only at unload or save, so until then read the actors, as the walk 0x51fd40 does: head [[0xe2d434]+layer*0x18+0x2c], next +0x14,
 * layers 9, 0xc, 0xd (0xccfeb0), skipping (+0xc&7) 3 and 4 (0x5201d0). Slot +0xff0 (0x526510), HP +0x1030 (0x522df0). Every loaded room counts, so the partner's too. */
static unsigned live_killed[RE0_KILLED_WORDS];
static void read_actors(void) {
 enum {LAYER=0x18,HEAD=0x2c,NEXT=0x14,STATE=0xc,SLOT=0xff0,HP=0x1030,MAX_ACTORS=2048};
 static const unsigned layers[3]={9,0xc,0xd};
 memset(live_killed,0,sizeof(live_killed));
 const BYTE *owner=(const BYTE *)(uintptr_t)u32(VA(0xe2d434));
 if(!owner||!readable(owner,0xd*LAYER+HEAD+4)){if(!diag.actors_unreadable++)log_line("Actor lists unreadable; kills show only after leaving the room\r\n");return;}
 for(unsigned l=0;l<3;l++) {
  const BYTE *a=(const BYTE *)(uintptr_t)u32(owner+layers[l]*LAYER+HEAD);unsigned n=0;
  while(a) {
   if(n++>=MAX_ACTORS){if(!diag.actors_overflow++)log_line("Actor list longer than expected; rest not read\r\n");break;}
   if(!readable(a,HP+4)){if(!diag.actors_unreadable++)log_line("Actor unreadable; rest of its list not read\r\n");break;}
   const unsigned state=u32(a+STATE)&7;
   if(state!=3&&state!=4)re0_arrange_note_actor(&live_arrange,live_killed,(int)u32(a+SLOT),(int)u32(a+HP));
   a=(const BYTE *)(uintptr_t)u32(a+NEXT);
  }
 }
 live_arrange.killed=live_killed;
}
static void read_arrange(void) {
 enum {ROWS_END=0x30+0x4e8*0x5c,COUNT=0x24fac,MODE=0x24ff0};
 const BYTE *mgr=(const BYTE *)(uintptr_t)u32(VA(0xdcc010));
 diag.arrange_mismatch+=live_arrange.mismatches;
 live_arrange=(RE0ArrangeView){0,0,0,0};
 if(!mgr||!readable(mgr,ROWS_END)||!readable(mgr+COUNT,MODE-COUNT+4)){if(!diag.arrange_unreadable++)log_line("Placement table unreadable; taken items stay shown\r\n");return;}
 live_arrange=(RE0ArrangeView){u32(mgr+COUNT),mgr,0,0};live_table_mode=(int)u32(mgr+MODE);read_actors();
 /* The game's difficulty when it is known; the INI value in other modes. */
 const int difficulty=re0_arrange_difficulty(&live_arrange);
 if(difficulty>=0)cfg.difficulty=difficulty;else cfg.difficulty=ini_difficulty;
}
/* An unknown table leaves every taken item shown, so say which one it was. */
static void report_table(void) {
 static unsigned logged=0xffffffff,changes;
 if(live_arrange.count==logged||changes>=8)return;
 char text[96];logged=live_arrange.count;changes++;snprintf(text,sizeof(text),"Placement table rows=%u mode=%d difficulty=%d\r\n",live_arrange.count,live_table_mode,re0_arrange_difficulty(&live_arrange));log_line(text);
}
/* The game's screen fade, [[0xdcbea4]+0x20]. Its update 0x5aa060 keeps the current colour at +0x274, alpha at +0x277, which it tests itself (0x5aa09d).
 * Drawing below this alpha starts a little before a fade in ends and stops a little after a fade out starts, as the user asked. Raise it to overlap the fades more. */
#define FADE_DRAW_ALPHA 64
static int screen_clear(void) {
 BYTE *owner=(BYTE *)(uintptr_t)u32(VA(0xdcbea4)),*fade=owner&&readable(owner+0x20,4)?(BYTE *)(uintptr_t)u32(owner+0x20):0;
 if(!fade||!readable(fade+0x274,4)){if(!diag.fade_unreadable++)log_line("Screen fade unreadable; overlay not gated\r\n");return 1;}
 return fade[0x277]<=FADE_DRAW_ALPHA;
}
/* The map object's own state, read again at Present: the draw hook only saw it while the map drew. Same test as map_draw's. */
static int map_live(const Capture *c){return c->map&&readable(c->map,0x280)&&u32(c->map)==0xcdc650&&u32(c->map+0x27c)==3;}
static RE0DrawGate present_gate;static unsigned gate_held;
/* User 2026-11-06, with RE0.NoUIWait's fast fade: the fade came back to clear while the closed map's last capture was still young, and drew it. */
static int overlay_allowed(const Capture *c,int clear){
 const int live=map_live(c);
 const int allowed=re0_present_gate(&present_gate,c->generation,clear,live);
 if(!allowed&&clear&&gate_held++<8)log_line("Overlay held back: no map draw since the fade or the map is not live\r\n");
 return allowed;
}
static void capture_report(const Capture *c,unsigned width,unsigned height) {
 char body[32768],tmp[MAX_PATH];size_t at=0;
 #define APPEND(...) do {int wrote=snprintf(body+at,sizeof(body)-at,__VA_ARGS__);if(wrote<0||(size_t)wrote>=sizeof(body)-at)return;at+=(size_t)wrote;} while(0)
 APPEND("{\"schema_version\":1,\"evidence\":\"captured-native-draw\",\"profile_sha256\":\"%s\",\"region\":%d,\"target\":[%u,%u],\"settings\":{\"enabled\":%d,\"names\":%d,\"english\":%d,\"size\":%d,\"opacity\":%d,\"difficulty\":%d,\"contents\":%u,\"selected\":%d,\"scope\":%d},\"rooms\":[",capture_profile,c->region,width,height,cfg.enabled,cfg.names,cfg.english,cfg.size,cfg.opacity,cfg.difficulty,cfg.mask,cfg.selected,cfg.scope);
 int first=1;
 for(unsigned i=0;i<ROOM_COUNT;i++)if(c->seen[i]){RE0Box b=c->room[i];APPEND("%s{\"index\":%u,\"box\":[%.6f,%.6f,%.6f,%.6f],\"state\":%d}",first?"":",",i,b.l,b.t,b.r,b.b,re0_frame_room_state(i,live_flags));first=0;}
 APPEND("],\"obstacles\":[");
 for(unsigned i=0;i<c->n_obstacles;i++){RE0Box b=c->obstacles[i];APPEND("%s[%.6f,%.6f,%.6f,%.6f]",i?",":"",b.l,b.t,b.r,b.b);}
 APPEND("],\"flags\":[");
 for(unsigned i=0;i<RE0_FLAG_WORDS;i++)APPEND("%s%u",i?",":"",live_flags[i]);
 /* Native piece state of every piece, drawn or not, one digit each; the flags above reproduce it. */
 APPEND("],\"room_states\":\"");
 for(unsigned i=0;i<ROOM_COUNT;i++)APPEND("%d",re0_frame_room_state(i,live_flags));
 APPEND("\",\"table_mode\":%d,\"table_rows\":%u,\"markers_done\":[",live_table_mode,live_arrange.count);
 first=1;for(unsigned i=0;i<re0_frame_marker_count();i++)if(re0_frame_marker_done(i,live_flags,&live_arrange)){APPEND("%s%u",first?"":",",i);first=0;}
 APPEND("]}\n");
 #undef APPEND
 if(snprintf(tmp,sizeof(tmp),"%s.tmp",report_path)>=(int)sizeof(tmp))return;
 HANDLE f=CreateFileA(tmp,GENERIC_WRITE,0,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);if(f==INVALID_HANDLE_VALUE)return;
 DWORD n;int ok=WriteFile(f,body,(DWORD)at,&n,0)&&n==at&&FlushFileBuffers(f);CloseHandle(f);
 if(!ok||!MoveFileExA(tmp,report_path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))log_line("Capture write failed; previous capture retained\r\n");
 else log_line("Native draw capture saved with progress flags; no save file read\r\n");
}
/* Evidence for the pan size report: what sets the name size, whenever it changes or a pan starts or stops at rest zoom. */
static void zoom_log(const Capture *c,unsigned height,int forced) {
 static int last_view=-1,last_z,last_size,last_panning,lines;static unsigned last_height;
 if(c->zoom_mode&&!forced)return;
 RE0View v;const int have=re0_layout_view(c->seen,c->room,&v);const float screen=(float)height/720.0f,z=have?re0_frame_name_zoom(&v,screen):0;const int zi=(int)(z*1000);
 if(!forced&&have==last_view&&zi==last_z&&cfg.size==last_size&&height==last_height&&c->panning==last_panning)return;
 last_view=have;last_z=zi;last_size=cfg.size;last_height=height;last_panning=c->panning;
 if(lines>=64)return;lines++;
 char text[200];snprintf(text,sizeof(text),"Name zoom%s: t=%.3f mode=%d pan=%.1f,%.1f panning=%d view=%d scale=%.4f name_zoom=%.3f size=%d back_h=%u\r\n",forced?" F8":"",(double)c->zoom_t,c->zoom_mode,(double)c->pan_x,(double)c->pan_y,c->panning,have,have?(double)v.scale:0.0,(double)z,cfg.size,height);log_line(text);
}
/* Diagnostic, user 2026-11-05: table rows past the count, where dropped items are expected. Reads only. Never overwrites: a new numbered file, at most ROWS_FILES. */
enum {ROWS_SLOTS=0x4e8,ROWS_STEP=0x5c,ROWS_FIRST=0x30,ROWS_LINK=0x2c,ROWS_COUNT=0x24fac,ROWS_MODE=0x24ff0,ROWS_FILES=32};
static char rows_text[(ROWS_SLOTS+1)*(ROWS_STEP*2+64)];
static unsigned rows_invalid,rows_capped,rows_failed;
static size_t put_text(char *o,const char *s){size_t n=0;while(s[n]){o[n]=s[n];n++;}return n;}
static size_t put_uint(char *o,unsigned v){char t[10];size_t n=0,k=0;do{t[n++]=(char)('0'+v%10);v/=10;}while(v);while(n)o[k++]=t[--n];return k;}
/* Length of the JSON, or 0 when the manager is not there or its count is out of bounds. */
static size_t rows_format(void) {
 const BYTE *mgr=(const BYTE *)(uintptr_t)u32(VA(0xdcc010));
 if(!mgr||!readable(mgr,ROWS_MODE+4)||!readable(mgr,ROWS_FIRST+ROWS_SLOTS*ROWS_STEP))return 0;
 const unsigned count=u32(mgr+ROWS_COUNT);
 if(count>ROWS_SLOTS)return 0;
 size_t at=put_text(rows_text,"{\"schema_version\":1,\"evidence\":\"captured-arrange-rows\",\"count\":");
 at+=put_uint(rows_text+at,count);at+=put_text(rows_text+at,",\"mode\":");at+=put_uint(rows_text+at,u32(mgr+ROWS_MODE));at+=put_text(rows_text+at,",\"rows\":[");
 for(unsigned s=count;s<ROWS_SLOTS;s++) {
  if(s>count)rows_text[at++]=',';
  at+=put_text(rows_text+at,"{\"slot\":");at+=put_uint(rows_text+at,s);at+=put_text(rows_text+at,",\"link\":");at+=put_uint(rows_text+at,u32(mgr+ROWS_LINK+s*ROWS_STEP));at+=put_text(rows_text+at,",\"hex\":\"");
  at+=put_hex(rows_text+at,mgr+ROWS_FIRST+s*ROWS_STEP,ROWS_STEP);at+=put_text(rows_text+at,"\"}");
 }
 return at+put_text(rows_text+at,"]}\n");
}
/* Each F8, for the partner and scenario cases not traced yet; and once per unmapped id. */
/* Live candidate 36: names of dropped items not seen though the shared code emits them. Which ops the frame has at F8, to see where they go. */
static RE0DrawOp last_ops[8];static unsigned last_ops_n;
static void drop_log(void) {
 const RE0DropStats *d=re0_frame_drop_stats();{char line[120];for(unsigned i=0;i<last_ops_n;i++){snprintf(line,sizeof(line),"Last op %u: glyph=%d box=%.0f,%.0f,%.0f,%.0f color=%08x\r\n",i,last_ops[i].glyph,(double)last_ops[i].l,(double)last_ops[i].t,(double)last_ops[i].r,(double)last_ops[i].b,last_ops[i].color);log_line(line);}}char text[140];snprintf(text,sizeof(text),"Drops: valid=%u drawn=%u unmapped=%u rejected=%u capped=%u last_unmapped=%u\r\n",d->valid,d->drawn,d->unmapped,d->rejected,d->capped,d->last_unmapped);log_line(text);
}
static void rows_dump(void) {
 const size_t n=rows_format();char text[120];
 if(!n){rows_invalid++;snprintf(text,sizeof(text),"Rows dump skipped: manager or count invalid (%u)\r\n",rows_invalid);log_line(text);return;}
 char path[MAX_PATH];snprintf(path,sizeof(path),"%s",report_path);char *dot=strrchr(path,'-');if(!dot||(size_t)(dot-path)+24>=sizeof(path)){rows_failed++;log_line("Rows dump skipped: path\r\n");return;}
 for(unsigned i=1;i<=ROWS_FILES;i++) {
  sprintf(dot,"-rows-%02u.json",i);
  HANDLE f=CreateFileA(path,GENERIC_WRITE,0,0,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,0);
  if(f==INVALID_HANDLE_VALUE){if(GetLastError()==ERROR_FILE_EXISTS)continue;break;}
  DWORD w=0;const int ok=WriteFile(f,rows_text,(DWORD)n,&w,0)&&w==n;CloseHandle(f);
  if(!ok)rows_failed++;
  snprintf(text,sizeof(text),"Rows dump %s: rows-%02u\r\n",ok?"saved":"write failed",i);log_line(text);return;
 }
 rows_capped++;snprintf(text,sizeof(text),"Rows dump skipped: no free file of %d, or create failed (%u)\r\n",ROWS_FILES,rows_capped);log_line(text);
}
static void input(const Capture *c,unsigned width,unsigned height) {
 DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);
 if(pid!=GetCurrentProcessId())return;
 int changed=0;
 /* Ctrl, not Shift: the game binds Shift to aim (config.ini KC_kamae=KB_SHIFT); no game binding uses Ctrl. */
 const int ctrl=!!(GetAsyncKeyState(VK_CONTROL)&0x8000);
 if(edge('H'))changed|=re0_settings_key(&cfg,'h',c->seen,live_flags);
 for(int key='0';key<='9';key++)if(edge(key))changed|=re0_settings_key(&cfg,key,c->seen,live_flags);
 if(edge(VK_OEM_4))changed|=re0_settings_key(&cfg,ctrl?'o':'[',c->seen,live_flags);
 if(edge(VK_OEM_6))changed|=re0_settings_key(&cfg,ctrl?'O':']',c->seen,live_flags);
 if(edge(VK_OEM_5))changed|=re0_settings_key(&cfg,'\\',c->seen,live_flags); /* backslash, Won on Korean keyboards: language */
 if(edge(VK_OEM_3))changed|=re0_settings_key(&cfg,'`',c->seen,live_flags); /* ~ key, left of 1: not bound by the game (config.ini) */
 if(edge(VK_OEM_COMMA))re0_settings_key(&cfg,',',c->seen,live_flags);
 if(edge(VK_OEM_PERIOD))re0_settings_key(&cfg,'.',c->seen,live_flags);
 if(edge(VK_OEM_MINUS)|edge(VK_SUBTRACT))changed|=re0_settings_key(&cfg,ctrl?'i':'-',c->seen,live_flags);
 if(edge(VK_OEM_PLUS)|edge(VK_ADD))changed|=re0_settings_key(&cfg,ctrl?'I':'+',c->seen,live_flags);
 if(changed)settings_save();
 if(edge(VK_F8)){zoom_log(c,height,1);capture_report(c,width,height);diag_report("F8");rows_dump();drop_log();if(!dump.state)InterlockedExchange(&dump.state,1);}
}
/* The call the review page makes, with the same view: what the emulator shows, the game shows. */
#define OVERLAY_OPS 8192
static unsigned overlay_ops(const Capture *c,unsigned width,unsigned height,RE0DrawOp *ops) {
 RE0View view;const int fixed=re0_layout_view(c->seen,c->room,&view);
 RE0Box edge[2]={{0}};
 for(unsigned i=0;i<2;i++)if(gradient_seen[i]&&present_count-gradient_at[i]<=2)edge[i]=gradient[i];
 re0_frame_set_map(re0_display_bounds(c->area,c->display_mode,edge[0],edge[1]));re0_frame_set_viewport(re0_display_area(c->area,c->display_mode));
 re0_frame_set_chrome(frame_shown(),(frame_map.r-frame_map.l)/1280.0f,(frame_map.b-frame_map.t)/720.0f,frame_map.l,frame_map.t);
 return re0_frame_ops(&cfg,(float)width,(float)height,c->seen,c->room,c->obstacles,c->n_obstacles,fixed?&view:0,0,live_flags,&live_arrange,ops,OVERLAY_OPS,0,0);
}
static void overlay(IDirect3DDevice9 *dev,Capture *c) {
 if(c->region<0||GetTickCount()-c->tick>250)return;
 /* Present is the one point where the back buffer holds the finished frame; EndScene may be an intermediate pass. */
 IDirect3DSurface9 *surface=0;D3DSURFACE_DESC desc;
 if(FAILED(IDirect3DDevice9_GetBackBuffer(dev,0,0,D3DBACKBUFFER_TYPE_MONO,&surface))){static int w;if(!w++)log_line("GetBackBuffer failed; overlay skipped\r\n");return;}
 HRESULT hr=IDirect3DSurface9_GetDesc(surface,&desc);
 if(FAILED(hr)||!desc.Width||!desc.Height){IDirect3DSurface9_Release(surface);return;}
 static DWORD first_map;if(!first_map)first_map=GetTickCount();
 static int reported;if(!reported&&GetTickCount()-first_map>2000){reported=1;diag_report("map open 2s");}
 read_flags();read_arrange();report_table();
 {RE0View fixed;if(!re0_layout_view(c->seen,c->room,&fixed)&&!diag.layout_rejected++)log_line("Captured room boxes disagree with static ones; names beside captured boxes, location marks off\r\n");}
 zoom_log(c,desc.Height,0);
 input(c,desc.Width,desc.Height);
 const int clear=screen_clear();static int was_clear=-1;static unsigned changes;
 if(clear!=was_clear){was_clear=clear;if(changes++<16){char text[64];snprintf(text,sizeof(text),"Screen fade gate %s\r\n",clear?"open":"closed");log_line(text);}}
 if(!overlay_allowed(c,clear)){IDirect3DSurface9_Release(surface);return;}
 static int target_logged;if(!target_logged++){char text[96];snprintf(text,sizeof(text),"Overlay back buffer %ux%u\r\n",desc.Width,desc.Height);log_line(text);}
  if(!load_atlas(dev)){static int warned;if(!warned++)log_line("Label atlas missing, invalid, or texture creation failed\r\n");IDirect3DSurface9_Release(surface);return;}
 load_icons(dev);
 IDirect3DStateBlock9 *state=0;
 if(FAILED(IDirect3DDevice9_CreateStateBlock(dev,D3DSBT_ALL,&state))){IDirect3DSurface9_Release(surface);return;}
 if(FAILED(IDirect3DStateBlock9_Capture(state))){IDirect3DStateBlock9_Release(state);IDirect3DSurface9_Release(surface);return;}
 IDirect3DSurface9 *old_target=0,*old_depth=0;
 IDirect3DDevice9_GetRenderTarget(dev,0,&old_target);IDirect3DDevice9_GetDepthStencilSurface(dev,&old_depth);
 IDirect3DDevice9_SetRenderTarget(dev,0,surface);IDirect3DDevice9_SetDepthStencilSurface(dev,0);
 int in_scene=SUCCEEDED(IDirect3DDevice9_BeginScene(dev));
 if(!in_scene){static int w;if(!w++)log_line("BeginScene failed at Present; overlay skipped\r\n");}
 if(in_scene){
 IDirect3DDevice9_SetVertexShader(dev,0);IDirect3DDevice9_SetPixelShader(dev,0);
 IDirect3DDevice9_SetFVF(dev,D3DFVF_XYZRHW|D3DFVF_DIFFUSE|D3DFVF_TEX1);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_ZENABLE,FALSE);IDirect3DDevice9_SetRenderState(dev,D3DRS_ZWRITEENABLE,FALSE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_ALPHATESTENABLE,FALSE);IDirect3DDevice9_SetRenderState(dev,D3DRS_ALPHABLENDENABLE,TRUE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_SRCBLEND,D3DBLEND_SRCALPHA);IDirect3DDevice9_SetRenderState(dev,D3DRS_DESTBLEND,D3DBLEND_INVSRCALPHA);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_BLENDOP,D3DBLENDOP_ADD);IDirect3DDevice9_SetRenderState(dev,D3DRS_SEPARATEALPHABLENDENABLE,FALSE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_CULLMODE,D3DCULL_NONE);IDirect3DDevice9_SetRenderState(dev,D3DRS_LIGHTING,FALSE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_FOGENABLE,FALSE);IDirect3DDevice9_SetRenderState(dev,D3DRS_STENCILENABLE,FALSE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_SCISSORTESTENABLE,FALSE);IDirect3DDevice9_SetRenderState(dev,D3DRS_SRGBWRITEENABLE,FALSE);
 IDirect3DDevice9_SetRenderState(dev,D3DRS_COLORWRITEENABLE,15);
 IDirect3DDevice9_SetTexture(dev,0,(IDirect3DBaseTexture9 *)atlas);
 IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_COLOROP,D3DTOP_MODULATE);IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_COLORARG1,D3DTA_TEXTURE);IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_COLORARG2,D3DTA_DIFFUSE);
 IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_ALPHAOP,D3DTOP_MODULATE);IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_ALPHAARG1,D3DTA_TEXTURE);IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_ALPHAARG2,D3DTA_DIFFUSE);
 IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_TEXTURETRANSFORMFLAGS,D3DTTFF_DISABLE);
 IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_TEXCOORDINDEX,0);
 IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_RESULTARG,D3DTA_CURRENT);
 IDirect3DDevice9_SetTextureStageState(dev,1,D3DTSS_COLOROP,D3DTOP_DISABLE);
 IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MINFILTER,D3DTEXF_LINEAR);IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MAGFILTER,D3DTEXF_LINEAR);
 IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MIPFILTER,D3DTEXF_NONE);IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_ADDRESSU,D3DTADDRESS_CLAMP);IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_ADDRESSV,D3DTADDRESS_CLAMP);
 IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_SRGBTEXTURE,FALSE);
 D3DVIEWPORT9 vp={0,0,desc.Width,desc.Height,0,1};IDirect3DDevice9_SetViewport(dev,&vp);
 static RE0DrawOp ops[OVERLAY_OPS];
 unsigned count=overlay_ops(c,desc.Width,desc.Height,ops);
 last_ops_n=count<8?count:8;memcpy(last_ops,ops+count-last_ops_n,last_ops_n*sizeof(RE0DrawOp));
 icons_bound=0; /* the atlas is bound above; the state block restores all of this for the game */
 for(unsigned i=0;i<count;i++)draw_op(dev,&ops[i]);
 IDirect3DDevice9_EndScene(dev);
 }
 if(old_target){IDirect3DDevice9_SetRenderTarget(dev,0,old_target);IDirect3DSurface9_Release(old_target);}
 IDirect3DDevice9_SetDepthStencilSurface(dev,old_depth);if(old_depth)IDirect3DSurface9_Release(old_depth);
 IDirect3DSurface9_Release(surface);
 if(FAILED(IDirect3DStateBlock9_Apply(state))){cfg.enabled=0;log_line("D3D state restore failed; overlay disabled\r\n");}
 IDirect3DStateBlock9_Release(state);if(in_scene)draws++;
 if(in_scene&&draws==1)log_line("First overlay frame submitted at Present; GPU appearance requires user review\r\n");
}
static HRESULT WINAPI present_hook(IDirect3DDevice9 *dev,const RECT *src,const RECT *dst,HWND window,const RGNDATA *dirty) {
 void **v=*(void ***)dev;PresentFn original=0;
 for(unsigned i=0;i<8;i++)if(chains[i].vtable==v){original=chains[i].present;break;}
 if(!original)return D3DERR_INVALIDCALL;
 /* Keep drawing the latest capture: Present can outpace map draws, and consuming it once would flicker. */
 static Capture c;EnterCriticalSection(&lock);c=pending;LeaveCriticalSection(&lock);
 present_count++;
 {static unsigned logged=0xffffffffu;const RE0DropStats *d=re0_frame_drop_stats();if(d->unmapped&&d->last_unmapped!=logged){logged=d->last_unmapped;drop_log();}}
 dump_step(c.region);
 if(c.generation)overlay(dev,&c);
 return original(dev,src,dst,window,dirty);
}
static int patch(void **slot,void *expected,void *replacement) {
 DWORD old;if(!VirtualProtect(slot,sizeof(*slot),PAGE_READWRITE,&old))return 0;
 void *seen=InterlockedCompareExchangePointer(slot,replacement,expected);
 DWORD unused;VirtualProtect(slot,sizeof(*slot),old,&unused);return seen==expected;
}
/* Shared with the offline native-dispatch harness so the real slots are what gets tested. */
static int patch_draw_slots(void) {
 original_map=(GuiDraw)VA(0x883090);original_instance=(GuiDraw)VA(0x87cc40);original_sprite=(GuiDraw)VA(0x890ae0);
 void **map_slot=(void **)VA(0xcdc6a8),**instance_slot=(void **)VA(0xd25478),**sprite_slot=(void **)VA(0xd26168);
 if(!patch(sprite_slot,(void *)original_sprite,(void *)sprite_draw)){log_line("Sprite vtable conflict; disabled\r\n");return 0;}
 if(!patch(instance_slot,(void *)original_instance,(void *)instance_draw)) {patch(sprite_slot,(void *)sprite_draw,(void *)original_sprite);log_line("Instance vtable conflict; disabled\r\n");return 0;}
 if(!patch(map_slot,(void *)original_map,(void *)map_draw)) {patch(instance_slot,(void *)instance_draw,(void *)original_instance);patch(sprite_slot,(void *)sprite_draw,(void *)original_sprite);log_line("Map vtable conflict; disabled\r\n");return 0;}
 return 1;
}
/* All scope, as RE1 HD: the piece state 0x5b4060 tests the region's map flag once per piece at 0x5b4afa, and state 0 skips the piece at 0x5b4b94. Answering yes there gives an unreached room state 2, grey, and turns on its doors (0x5b4d48), while a visited room stays green.
 * Reads only; no flag is written. The other tests of that flag stay native: 0x5b3c5b the regions on offer, 0x5bb998 the floor tabs. 0x5b4060 runs when the map opens and on a floor change (0x5b51b1, 0x5bb3d2), not per frame, so the outlines follow [8] from then on. */
typedef unsigned (__thiscall *FlagTest)(void *,unsigned);
#define MAP_FLAG_TEST 0x59b8d0
/* Only 0x5b4afa comes here, and hook_all_scope checks it asks for a map flag. */
static unsigned __fastcall flag_all_scope(void *owner,void *unused,unsigned index) {
 (void)unused;
 if(cfg.enabled&&cfg.scope==RE0_SCOPE_ALL)return 1;
 return ((FlagTest)VA(MAP_FLAG_TEST))(owner,index);
}
/* `add eax,0x2c8; push eax; call 0x59b8d0` at 0x5b4af4. Returns 1 when patched; a mismatch leaves the game as it is, and only outlines are lost. */
static int hook_all_scope(void) {
 BYTE *call_site=VA(0x5b4afa);
 static const BYTE context[6]={0x05,0xc8,0x02,0x00,0x00,0x50};
 if(!readable(call_site-6,11)||memcmp(call_site-6,context,6)||call_site[0]!=0xe8||call_site+5+(int)u32(call_site+1)!=VA(MAP_FLAG_TEST)){log_line("All-scope site mismatch; outlines of unreached rooms not drawn\r\n");return 0;}
 DWORD old;
 if(!VirtualProtect(call_site+1,4,PAGE_EXECUTE_READWRITE,&old)){log_line("All-scope patch refused; outlines of unreached rooms not drawn\r\n");return 0;}
 const int rel=(int)((BYTE *)flag_all_scope-(call_site+5));memcpy(call_site+1,&rel,4);
 VirtualProtect(call_site+1,4,old,&old);FlushInstructionCache(GetCurrentProcess(),call_site,5);
 return 1;
}
/* A silent retry loop hides why the overlay never appears, so log each new reason once. */
static void wait_state(const char *reason) {
 static const char *last;if(last==reason)return;last=reason;
 char text[96];snprintf(text,sizeof(text),"Waiting: %s\r\n",reason);log_line(text);
}
#ifndef RE0_MAP_VERSION
#define RE0_MAP_VERSION "dev" /* build.py passes VERSION */
#endif
static DWORD WINAPI install(void *unused) {
 (void)unused;
 settings_load();logfile=CreateFileA(log_path,GENERIC_WRITE,FILE_SHARE_READ,0,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);
 log_line("RE0 Annotated Map " RE0_MAP_VERSION "\r\n");
 if(!supported_exe()){log_line("Unsupported EXE base; disabled without hooks\r\n");return 0;}
 if(settings_migrated){log_line("Settings from an older build: migrated (sizes before Version 44: names /1.1, icons /1.3; ItemNames on -> 1; Contents: events off)\r\n");settings_save();}
 unsigned tick;
 for(tick=0;tick<2400;tick++,Sleep(50)) {
  if(readable(VA(0x883090),6)&&!memcmp(VA(0x883090),"\x55\x8b\xec\x83\xe4\xf8",6)&&
     !memcmp(VA(0x87cc40),"\x55\x8b\xec\x83\xe4\xf0",6)&&
     !memcmp(VA(0x890ae0),"\x56\x8b\xf1\x83\xbe\xe4",6))break;
 }
 if(tick==2400){log_line("Decrypted code signatures unavailable; disabled\r\n");return 0;}
 if(!patch_draw_slots())return 0;
 log_line("Native map/instance/sprite draw hooks ready\r\n");
 if(hook_all_scope())log_line("All-scope outline hook ready\r\n");
 for(;;Sleep(250)) {
  BYTE *renderer=(BYTE *)(uintptr_t)u32(VA(0xe2d40c));
  if(!readable(renderer,0x9c)){wait_state("renderer not created");continue;}
  /* Base sRender (seen live on candidate 1) or its 0x6021b9 subclass; accept only these two. */
  unsigned renderer_vt=u32(renderer);
  if(renderer_vt!=0xce5fc0&&renderer_vt!=0xd1b278){wait_state("unknown renderer vtable");continue;}
  IDirect3DDevice9 *dev=*(IDirect3DDevice9 **)(renderer+0x98);
  if(!readable(dev,4)){wait_state("device not created");continue;}
  void **vt=*(void ***)dev;if(!readable(vt,119*4)||!executable(vt[16])||!executable(vt[17])||!executable(vt[42])||!executable(vt[83])){wait_state("device vtable not usable");continue;}
  unsigned i;for(i=0;i<8&&chains[i].vtable&&chains[i].vtable!=vt;i++);
  if(i==8||vt[17]==(void *)present_hook)continue;
  /* Do not replace a remembered original with a later hook: avoid chain recursion. */
  if(chains[i].vtable){if(!chains[i].warned++)log_line("Present changed by another module; no rehook\r\n");continue;}
  chains[i].present=(PresentFn)vt[17];chains[i].vtable=vt;
  if(patch(&vt[17],(void *)chains[i].present,(void *)present_hook))log_line("D3D9 Present chained\r\n");
  else {chains[i].vtable=0;chains[i].present=0;wait_state("Present patch refused");}
 }
}
BOOL WINAPI DllMain(HINSTANCE dll,DWORD reason,LPVOID reserved) {
 (void)reserved;
 if(reason==DLL_PROCESS_ATTACH) {
  image=(BYTE *)dll;DisableThreadLibraryCalls(dll);InitializeCriticalSection(&lock);tls=TlsAlloc();
  if(tls==TLS_OUT_OF_INDEXES)return FALSE;
  if(!module_path(ini_path,"RE0.AnnotatedMap.ini")||!module_path(atlas_path,"RE0.AnnotatedMap.bgra")||!module_path(icon_path,"RE0.AnnotatedMap.icons.bgra")||!module_path(log_path,"RE0.AnnotatedMap.log")||!module_path(report_path,"RE0.AnnotatedMap-capture.json"))return FALSE;
  HANDLE thread=CreateThread(0,0,install,0,0,0);if(thread)CloseHandle(thread);else {TlsFree(tls);DeleteCriticalSection(&lock);return FALSE;}
 }
 return TRUE;
}

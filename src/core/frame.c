#include "frame.h"
#include <string.h>
#include "../runtime/labels_generated.h"
#define MAX_RESERVED 1536
#define MAX_OBSTACLE_SIDE 64
/* Row colours and gray sampled from the RE1 HD legend rasters. */
#define OFF_GRAY 0xff6a6a6au /* user 2026-11-08: darker than the common-item grey so a disabled row stays distinct */
#define ROOM_CREAM 0xfff0e2beu
#define SMALL_TEXT 0xffc8c8c8u
#define NOTE_TEXT 0xffa5a5a5u
#define VALUE_GOLD 0xffffe080u
/* By category id: lock, key, file, puzzle, item, enemy, event. The item colour is a cool grey (user 2026-11-08); [Colors] in the INI replaces any of them. */
static const unsigned default_color[RE0_CATEGORIES]={0xffffcd46u,0xff5adcffu,0xffff8cd2u,0xffff9628u,0xffb8bcc4u,0xffeb3c3cu,0xffb070ffu};
static unsigned category_color[RE0_CATEGORIES]={0xffffcd46u,0xff5adcffu,0xffff8cd2u,0xffff9628u,0xffb8bcc4u,0xffeb3c3cu,0xffb070ffu};
void re0_frame_set_color(unsigned c,unsigned rgb){if(c<RE0_CATEGORIES)category_color[c]=0xff000000u|(rgb&0xffffffu);}
unsigned re0_frame_color(unsigned c){return c<RE0_CATEGORIES?category_color[c]&0xffffffu:0;}
void re0_frame_reset_colors(void){for(unsigned i=0;i<RE0_CATEGORIES;i++)category_color[i]=default_color[i];}
/* Layout sizes below were set against 20 px art; this keeps them when the raster size changes. */
#define NAME_SCALE (20.0f/NAME_FONT)
/* User 2026-11-03: size 100 at full zoom. Room names are 80% of the earlier base; item names keep it. tools/extract/room_layout.py SCALE must match the room value at zoom out. */
#define ZOOM_OUT_NAME .7f
/* Candidate 44: the user's 110% name size and 130% icon size became the 100% defaults, so the old setting times these factors is the new one (re0_settings_migrate). */
#define NAME_SIZE_BASE 1.1f
#define ICON_SIZE_BASE 1.3f
#define ROOM_NAME_K (.88f*.8f*NAME_SIZE_BASE) /* RE2 Remake style, user: room names 20% smaller */
#define ITEM_NAME_K (.8f*.8f*NAME_SIZE_BASE) /* item names 20% smaller */
#define ICON_SIDE (18.0f*1.2f) /* candidate 45: enemies keep this; every other icon is ICON_SIZE_BASE times it, more zoomed in (icon_gain) */
static float lower(float a,float b){return a<b?a:b;}
static float upper(float a,float b){return a>b?a:b;}
static int boxes_hit(RE0Box a,RE0Box b){return a.l<b.r&&a.r>b.l&&a.t<b.b&&a.b>b.t;}
/* Native zoom runs map scale from 1x to 3x. Names are the set size zoomed in and 70% of it zoomed out, following the map through the zoom. */
static float zoom_name(const RE0View *v,float screen) {
 const float t=(v->scale/screen-1)*.5f;return ZOOM_OUT_NAME+(1-ZOOM_OUT_NAME)*(t<0?0:t>1?1:t);
}
static float zoom_t(const RE0View *v,float screen){const float t=(v->scale/screen-1)*.5f;return t<0?0:t>1?1:t;} /* 0 zoomed out, 1 at 3x */
float re0_frame_name_zoom(const RE0View *v,float screen){return zoom_name(v,screen);}
static int clamp(int v,int lo,int hi){return v<lo?lo:v>hi?hi:v;}
int re0_obstacle_fits(RE0Box b){return b.r-b.l<=MAX_OBSTACLE_SIDE&&b.b-b.t<=MAX_OBSTACLE_SIDE;}
unsigned re0_frame_room_count(void){return ROOM_COUNT;}
unsigned re0_frame_place_count(void){return PLACE_COUNT;}
unsigned re0_frame_marker_count(void){return MARKER_COUNT;}
int re0_present_gate(RE0DrawGate *gate,unsigned generation,int fade_clear,int map_live) {
 if(!fade_clear||!map_live){gate->stale=generation;return 0;}
 return generation>gate->stale;
}
void re0_settings_default(RE0Settings *s) {
 *s=(RE0Settings){.enabled=1,.names=1,.english=0,.size=100,.opacity=60,.difficulty=1,.mask=RE0_MASK_DEFAULT,.selected=-1,.hidden=0,.scope=RE0_SCOPE_VISITED,.icon_size=100,.icon_opacity=80,.item_names=0,.legend=1}; /* RE2 Remake style: item names off until H */
}
/* Sizes saved before candidate 44 are on the old scale: names 1/1.1, icons 1/1.3 of what they showed, rounded to the 10 step. Run once per INI. */
static int migrated_size(int old,float base,int lo,int hi){return clamp((int)((float)old/base+5.0f)/10*10,lo,hi);}
int re0_settings_ini_sizes(RE0Settings *s,int version,int name_size,int icon_size) {
 const int old=version<RE0_SIZE_SCALE_VERSION;
 s->size=name_size<0?100:old?migrated_size(clamp(name_size,50,150),NAME_SIZE_BASE,50,150):clamp(name_size,50,150);
 s->icon_size=icon_size<0?100:old?migrated_size(clamp(icon_size,50,200),ICON_SIZE_BASE,50,200):clamp(icon_size,50,200);
 return version<RE0_SETTINGS_VERSION;
}
/* ItemNames was on/off before Version 50: any non-zero was on, now 1. Later files hold 0, 1 or 2; anything else is off. */
int re0_settings_item_names(int version,int value){return version<RE0_ITEM_NAMES_VERSION?value!=0:value>=0&&value<=2?value:0;}
unsigned re0_settings_contents(int version,int value){const unsigned v=(unsigned)value&RE0_MASK_ALL;return version<RE0_CONTENTS_VERSION?v&63u:v;}
unsigned re0_legend_category(unsigned row){static const unsigned char order[7]={0,1,2,3,6,4,5};return order[row<7?row:6];}
int re0_color_parse(const char *t,unsigned *rgb){
 unsigned v=0,n=0;if(!t)return 0;while(*t==' '||*t=='\t')t++;if(*t=='#')t++;
 for(;n<6;n++,t++){const char c=*t;const int d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;if(d<0)return 0;v=v<<4|(unsigned)d;}
 while(*t==' '||*t=='\t')t++;
 if(*t&&*t!=';'&&*t!='\r'&&*t!='\n')return 0;
 *rgb=v;return 1;
}
/* ponytail: line scanner, no regex. Keys compare case-insensitively like GetPrivateProfile. */
static int ieq(char a,char b){return (a>='A'&&a<='Z'?a+32:a)==(b>='A'&&b<='Z'?b+32:b);}
/* Missing keys go after the section's last non-blank line, ahead of the blank lines that separate it from the next section. */
static int add_missing(char *out,unsigned *op,unsigned cap,const char *const *keys,const char *const *values,unsigned nk,unsigned *written) {
 unsigned o=*op,end=o;char blanks[128];unsigned nb;
 while(end>0&&out[end-1]=='\n'){unsigned ls=end-1;while(ls>0&&out[ls-1]!='\n')ls--;if(end-ls==1||(end-ls==2&&out[ls]=='\r'))end=ls;else break;}
 nb=o-end;if(nb>sizeof(blanks))nb=0,end=o;
 for(unsigned i=0;i<nb;i++)blanks[i]=out[end+i];
 o=end;
 for(unsigned k=0;k<nk;k++)if(!written[k]) {
  for(const char *q=keys[k];*q;q++){if(o>=cap)return 0;out[o++]=*q;}
  if(o+2>=cap)return 0;out[o++]='=';
  for(const char *q=values[k];*q;q++){if(o>=cap)return 0;out[o++]=*q;}
  if(o+2>cap)return 0;out[o++]='\r';out[o++]='\n';written[k]=1;
 }
 for(unsigned i=0;i<nb;i++){if(o>=cap)return 0;out[o++]=blanks[i];}
 *op=o;return 1;
}
unsigned re0_ini_merge(const char *old,unsigned old_n,const char *const *keys,const char *const *values,unsigned nk,const char *tail,char *out,unsigned cap) {
 unsigned o=0,written[32]={0};int in_map=0,have_map=0,have_colors=0;
 #define PUT(c) do{if(o>=cap)return 0;out[o++]=(c);}while(0)
 #define PUTS(s) do{for(const char *q_=(s);*q_;q_++)PUT(*q_);}while(0)
 if(nk>32)return 0;
 for(unsigned i=0;i<old_n;) {
  unsigned e=i;while(e<old_n&&old[e]!='\n')e++;
  const unsigned next=e<old_n?e+1:e;unsigned a=i,z=e;if(z>a&&old[z-1]=='\r')z--;
  while(a<z&&(old[a]==' '||old[a]=='\t'))a++;
  if(a<z&&old[a]=='[') {
   if(in_map&&!add_missing(out,&o,cap,keys,values,nk,written))return 0;
   in_map=0;unsigned c=a+1,b=0;static const char map[]="map",colors[]="colors";
   while(c<z&&old[c]!=']'&&ieq(old[c],map[b])&&b<3){c++;b++;}
   if(b==3&&c<z&&old[c]==']'){in_map=1;have_map=1;}
   else{c=a+1;b=0;while(c<z&&old[c]!=']'&&ieq(old[c],colors[b])&&b<6){c++;b++;}if(b==6&&c<z&&old[c]==']')have_colors=1;}
  } else if(in_map&&a<z&&old[a]!=';'&&old[a]!='#') {
   for(unsigned k=0;k<nk;k++) {
    unsigned n=0;while(keys[k][n])n++;
    unsigned m=0;while(m<n&&a+m<z&&ieq(old[a+m],keys[k][m]))m++;
    unsigned q=a+m;while(q<z&&(old[q]==' '||old[q]=='\t'))q++;
    if(m==n&&q<z&&old[q]=='='&&!written[k]) {
     PUTS(keys[k]);PUT('=');PUTS(values[k]);written[k]=1;
     if(e>z)PUT('\r');
     if(e<old_n)PUT('\n');
     goto next_line;
    }
   }
  }
  for(unsigned j=i;j<next;j++)PUT(old[j]);
  next_line:i=next;
 }
 if(old_n&&old[old_n-1]!='\n'){PUT('\r');PUT('\n');}
 if(in_map){if(!add_missing(out,&o,cap,keys,values,nk,written))return 0;}
 else if(!have_map){PUTS("[Map]\r\n");unsigned none[32]={0};if(!add_missing(out,&o,cap,keys,values,nk,none))return 0;}
 if(!have_colors&&tail)PUTS(tail);
 #undef PUT
 #undef PUTS
 return o;
}
static int flag_set(const unsigned *flags,unsigned flag){return flag!=0xffff&&(flags[flag>>5]>>(flag&31)&1);}
int re0_frame_room_state(unsigned i,const unsigned *flags) {
 if(i>=ROOM_COUNT||!flags)return 0;
 const RE0RoomState *r=&room_state[i];
 return (flag_set(flags,r->visited0)&&(r->visited1==0xffff||flag_set(flags,r->visited1)))|(flag_set(flags,r->revealed0)||flag_set(flags,r->revealed1))<<1;
}
static int same_floor(unsigned a,unsigned b){return rooms[a].region==rooms[b].region&&rooms[a].floor==rooms[b].floor;}
/* Which pieces annotations treat as on, from what the game drew. The game draws one piece of a room by state and marks and names are tied to one piece each, so a drawn piece lights its whole place on that floor.
 * All scope lights the floor of anything drawn, as the drawn rooms give the map's view. Unknown flags: what was drawn counts. */
static void scope_rooms(const RE0Settings *s,const unsigned *flags,const unsigned char *drawn,unsigned char *on) {
 memset(on,0,ROOM_COUNT);
 for(unsigned i=0;i<ROOM_COUNT;i++)if(drawn[i]) {
  const int state=re0_frame_room_state(i,flags),allowed=!flags||(s->scope==RE0_SCOPE_REVEALED?state!=0:state&1);
  for(unsigned j=0;j<ROOM_COUNT;j++)if(same_floor(i,j)&&(s->scope==RE0_SCOPE_ALL||(allowed&&rooms[j].place==rooms[i].place)))on[j]=1;
 }
}
typedef struct {RE0Box box[PLACE_COUNT];unsigned char seen[PLACE_COUNT];} Shown;
static void merge_places(const unsigned char *room_seen,const RE0Box *room_box,Shown *out) {
 memset(out,0,sizeof(*out));
 for(unsigned i=0;i<ROOM_COUNT;i++)if(room_seen[i]) {
  unsigned p=rooms[i].place;RE0Box b=room_box?room_box[i]:(RE0Box){0,0,0,0},*m=&out->box[p];
  if(!out->seen[p])*m=b;else {m->l=lower(m->l,b.l);m->t=lower(m->t,b.t);m->r=upper(m->r,b.r);m->b=upper(m->b,b.b);}
  out->seen[p]=1;
 }
}
static void step_selection(RE0Settings *s,const Shown *shown,int direction) {
 int p=s->selected;
 if(p<-1||p>=PLACE_COUNT)p=-1;
 /* -1 means no room selected, so one full lap passes through it. */
 for(int i=0;i<PLACE_COUNT+1;i++) {
  p+=direction;
  if(p>=PLACE_COUNT)p=-1;else if(p<-1)p=PLACE_COUNT-1;
  if(p==-1||shown->seen[p]){s->selected=p;return;}
 }
}
int re0_settings_key(RE0Settings *s,int key,const unsigned char *room_seen,const unsigned *flags) {
 if(key=='0'){s->enabled=!s->enabled;return 1;}
 if(key=='1'){s->names=!s->names;return 1;}
 if(key>='2'&&key<='8'){s->mask^=1u<<re0_legend_category((unsigned)(key-'2'));return 1;} /* user 2026-11-08: 2 locks .. 8 enemies */
 if(key=='9'){s->scope=(s->scope+1)%3;return 1;}
 if(key=='\\'){s->english=!s->english;return 1;} /* VK_OEM_5, the backslash key (Won on Korean keyboards) */
 if(key=='-'||key=='+'){s->size=clamp(s->size+(key=='+'?10:-10),50,150);return 1;}
 if(key=='['||key==']'){s->opacity=clamp(s->opacity+(key==']'?10:-10),10,100);return 1;}
 /* Ctrl with the same keys, user 2026-11-06: icon size i/I and icon opacity o/O; H toggles item names. */
 if(key=='i'||key=='I'){s->icon_size=clamp(s->icon_size+(key=='I'?10:-10),50,200);return 1;}
 if(key=='o'||key=='O'){s->icon_opacity=clamp(s->icon_opacity+(key=='O'?10:-10),10,100);return 1;}
 if(key=='h'){s->item_names=(s->item_names+1)%3;return 1;} /* User 2026-11-08: all (1) -> all except common (2) -> off (0) -> all */
 if(key=='`'){s->legend=!s->legend;return 1;} /* VK_OEM_3, RE2 annotated map's key */
 if((key==','||key=='.')&&room_seen) {
  unsigned char on[ROOM_COUNT];Shown shown;scope_rooms(s,flags,room_seen,on);merge_places(on,0,&shown);step_selection(s,&shown,key=='.'?1:-1);
 }
 return 0;
}
typedef struct {RE0DrawOp *ops;unsigned n,cap;} List;
static void add(List *l,float x0,float y0,float x1,float y1,unsigned color,int glyph) {
 if(l->n<l->cap)l->ops[l->n++]=(RE0DrawOp){x0,y0,x1,y1,color,glyph};
}
static float add_text(List *l,unsigned g,float x,float y,float k,unsigned color) {
 add(l,x,y,x+glyphs[g].w*k,y+glyphs[g].h*k,color,(int)g);return y+glyphs[g].h*k;
}
static float percent_width(int value,float k) {
 float w=glyphs[SMALL_PERCENT_ID].w*k;
 for(int divisor=value>=100?100:10;divisor;divisor/=10)w+=(glyphs[small_digit_ids[value/divisor%10]].w-9)*k;
 return w;
}
static void add_percent(List *l,int value,float x,float y,float k,unsigned color) {
 int divisor=value>=100?100:10;
 for(;divisor;divisor/=10) {unsigned g=small_digit_ids[value/divisor%10];add_text(l,g,x,y,k,color);x+=glyphs[g].w*k-9*k;}
 add_text(l,SMALL_PERCENT_ID,x,y,k,color);
}
/* Where the game draws its map inside the back buffer (re0_map_viewport). Original (4:3) leaves black bars the overlay must stay out of; everything below that places or clips something uses it, not the buffer. Set per frame from the game's rectangle; unset means the whole buffer. */
static RE0Box map_given,area={0,0,1,1};static int map_known;
/* Candidate 54: a mark or name may overlap the frame or the side gradient by `slack` (half a default icon, so a default mark goes when its centre crosses) before it is hidden. `reach` is the area grown by it, never past the viewport itself (Original's black bars stay strict). */
static RE0Box hard,reach;static int hard_known;static float slack,edge_l,edge_r; /* edge_l/edge_r: the visible map's own left/right edge (display box), where the legend and readouts sit */
void re0_frame_set_map(RE0Box b){map_known=b.r>b.l&&b.b>b.t;map_given=b;hard_known=0;}
void re0_frame_set_viewport(RE0Box v){hard=v;hard_known=v.r>v.l&&v.b>v.t;}
RE0Box re0_frame_map(void){return area;}
/* RE1 HD layout: dark panel bottom-left, title, rows [0]..[3] | [4]..[7], [8] | [9], then hints. The name and icon readouts have their own panel (readout_ops).
 * A row off is the same row in gray. Stays visible through 0 and held H so a toggle can always be read and undone.
 * [~] folds it to one hint line, as the RE2 annotated map does; the readouts and everything else stay. */
static RE0Box legend_ops(const RE0Settings *s,float k,List *l) {
 const unsigned lang=s->english?1:0;
 const float pad=12*k,gap=22*k,lh=30*k;
 if(!s->legend) {
  const float w=glyphs[fold_ids[lang]].w*k,h=glyphs[fold_ids[lang]].h*k,x0=edge_l+28*k,y0=area.b-28*k-(h+2*pad);
  RE0Box box={x0,y0,x0+w+2*pad,y0+h+2*pad};add(l,box.l,box.t,box.r,box.b,0xd0080808u,-1);
  add_text(l,fold_ids[lang],x0+pad,y0+pad,k,SMALL_TEXT);return box;
 }
 /* User 2026-11-08, two columns: [0]..[4] | [5]..[8] and [9] under them; below, on one hint-size line, [H] item names under the left column and [\] language under the right. */
 float col[2]={0,0};
 for(unsigned r=0;r<9;r++){float w=glyphs[row_ids[r*2+lang]].w*k;if(w>col[r<5?0:1])col[r<5?0:1]=w;}
 for(unsigned i=0;i<3;i++){col[0]=upper(col[0],glyphs[hold_ids[i*2+lang]].w*k);col[1]=upper(col[1],glyphs[scope_ids[i*2+lang]].w*k);} /* the widest [H] state, so the panel holds still as H cycles */
 col[1]=upper(col[1],glyphs[language_ids[lang]].w*k);
 const float tw=glyphs[title_ids[lang]].w*k,th=glyphs[title_ids[lang]].h*k,hh=th+6*k,cw=col[0]+gap+col[1];
 const float hide_gap=14*k,hw=tw+hide_gap+glyphs[hide_ids[lang]].w*k;
 const float w=2*pad+upper(cw,hw);
 const float h=2*pad+hh+5*lh+lh*.85f,x0=edge_l+28*k,y0=area.b-28*k-h;
 RE0Box box={x0,y0,x0+w,y0+h};add(l,box.l,box.t,box.r,box.b,0xd0080808u,-1);
 float x=x0+pad,y=y0+pad;
 add_text(l,title_ids[lang],x,y,k,0xffffffffu);
 add_text(l,hide_ids[lang],x+tw+hide_gap,y+th-glyphs[hide_ids[lang]].h*k,k,SMALL_TEXT); /* the fold hint sits beside the title */
 y+=hh;
 const float x1=x+col[0]+gap;
 for(unsigned r=0;r<9;r++) {
  int on=!!s->enabled;unsigned color=0xffffffffu;
  if(r==1){on=on&&s->names;color=ROOM_CREAM;}
  else if(r>=2){const unsigned c=re0_legend_category(r-2);on=on&&((s->mask>>c)&1);color=category_color[c];}
  add_text(l,row_ids[r*2+lang],r<5?x:x1,y+(float)(r<5?r:r-5)*lh,k,on?color:OFF_GRAY);
 }
 add_text(l,scope_ids[s->scope*2+lang],x1,y+4*lh,k,0xffffffffu); /* [9] ends the right column */
 y+=5*lh;
 add_text(l,hold_ids[(s->item_names>=0&&s->item_names<3?s->item_names:0)*2+lang],x,y,k,s->item_names?SMALL_TEXT:OFF_GRAY);
 add_text(l,language_ids[lang],x1,y,k,SMALL_TEXT);
 return box;
}
/* Name and icon opacity/size readouts, bottom-right, the legend's margins mirrored. Like the legend it is ours and stays on top of the frame. */
static RE0Box readout_ops(const RE0Settings *s,float k,List *l) {
 const unsigned lang=s->english?1:0;
 const unsigned label[4]={opacity_ids[lang],size_ids[lang],icon_opacity_ids[lang],icon_size_ids[lang]};
 const int value[4]={s->opacity,s->size,s->icon_opacity,s->icon_size};
 const float pad=12*k;float lw=0,h=0;
 for(unsigned i=0;i<4;i++){lw=upper(lw,glyphs[label[i]].w*k);h+=glyphs[label[i]].h*k;}
 /* Value column as wide as the widest, 100%: the panel does not breathe as a value changes. */
 const float vw=percent_width(100,k);
 const float w=2*pad+lw+vw+8*k,hh=2*pad+h,x0=edge_r-28*k-w,y0=area.b-28*k-hh;
 RE0Box box={x0,y0,x0+w,y0+hh};add(l,box.l,box.t,box.r,box.b,0xd0080808u,-1);
 float y=y0+pad;
 for(unsigned i=0;i<4;i++){add_text(l,label[i],x0+pad,y,k,SMALL_TEXT);add_percent(l,value[i],x0+pad+lw+8*k+vw-percent_width(value[i],k),y,k,VALUE_GOLD);y+=glyphs[label[i]].h*k;} /* values right-aligned */
 return box;
}
/* Selected room: name, exits and listed contents, beside the legend. */
static RE0Box panel_ops(const RE0Settings *s,const Shown *shown,float x,float bottom,float scale,const unsigned *flags,List *l) {
 enum {MAX_ROWS=26};
 const Place *p=&places[s->selected];unsigned rows[MAX_ROWS],colors[MAX_ROWS],n=0,lang=s->english?1:0,more=0,visible=0;
 rows[n]=s->english?p->en:p->ko;colors[n++]=0xffffffffu;
 rows[n]=mode_ids[s->difficulty*2+lang];colors[n++]=VALUE_GOLD;
 if(p->links){rows[n]=panel_ids[lang];colors[n++]=0xffa0a0a0u;}
 for(unsigned i=0;i<p->links&&n<MAX_ROWS;i++){const Place *t=&places[place_links[p->first_link+i]];rows[n]=s->english?t->en:t->ko;colors[n++]=0xffd0d0d0u;}
 for(unsigned i=0;i<p->count;i++) {
  const RE0Content *row=&contents[p->first+i];
  if(!re0_content_count(row,(unsigned)s->difficulty,s->mask,flags))continue;
  visible++;
  if(n<MAX_ROWS){rows[n]=s->english?row->en:row->ko;colors[n++]=category_color[row->category];}else more=1;
 }
 if(!visible&&n<MAX_ROWS){rows[n]=panel_ids[2+lang];colors[n++]=0xffa0a0a0u;}
 if(more)rows[n-1]=panel_ids[4+lang];
 float w=0,h=0;
 for(unsigned i=0;i<n;i++)h+=glyphs[rows[i]].h*scale+1;
 if(h+24>bottom){scale*=(bottom-24)/h;h=bottom-24;}
 for(unsigned i=0;i<n;i++)w=upper(w,glyphs[rows[i]].w*scale);
 const float top=bottom-h-8;
 RE0Box panel={x,top,x+w+8,bottom};add(l,panel.l,panel.t,panel.r,panel.b,0xc0080808u,-1);
 float y=top+4;for(unsigned i=0;i<n;i++)y=add_text(l,rows[i],x+4,y,scale,colors[i])+1;
 RE0Box b=shown->box[s->selected];const float t=2;
 add(l,b.l-t,b.t-t,b.r+t,b.t,0xffffe040u,-1);add(l,b.l-t,b.b,b.r+t,b.b+t,0xffffe040u,-1);
 add(l,b.l-t,b.t,b.l,b.b,0xffffe040u,-1);add(l,b.r,b.t,b.r+t,b.b,0xffffe040u,-1);
 return panel;
}
static float badge_width(const unsigned counts[RE0_CATEGORIES],float k,float *height) {
 float w=0;*height=0;
 for(unsigned i=0;i<RE0_CATEGORIES;i++)if(counts[i]) {
  unsigned d=counts[i]>9?9:counts[i];
  w+=(glyphs[badge_ids[i]].w+glyphs[digit_ids[d]].w)*k;
  *height=upper(*height,glyphs[badge_ids[i]].h*k);
 }
 return w;
}
/* A label pushed outside its room gets an elbow line to the room centre: dark casing, light core, end dot. */
static void leader_ops(const RE0Box *label,const RE0Box *room,float screen,unsigned alpha,List *l) {
 const float rx=(room->l+room->r)*.5f,ry=(room->t+room->b)*.5f,lx=(label->l+label->r)*.5f,ly=(label->t+label->b)*.5f;
 if(lx>=room->l&&lx<=room->r&&ly>=room->t&&ly<=room->b)return;
 const float sx=rx<label->l?label->l:rx>label->r?label->r:rx,sy=ry<label->t?label->t:ry>label->b?label->b:ry,t=upper(1,screen*.75f);
 for(int pass=0;pass<2;pass++) {
  const float w=pass?t:t+screen*1.5f;const unsigned color=pass?alpha|0xf8f0c8u:alpha|0x080808u;
  add(l,sx-w*.5f,lower(sy,ry)-w*.5f,sx+w*.5f,upper(sy,ry)+w*.5f,color,-1);
  add(l,lower(sx,rx)-w*.5f,ry-w*.5f,upper(sx,rx)+w*.5f,ry+w*.5f,color,-1);
  add(l,rx-w*1.5f,ry-w*1.5f,rx+w*1.5f,ry+w*1.5f,color,-1);
 }
}
/* A room on screen always gets its name when there is any room. Free space first; then rings further out, which leader_ops ties back;
 * last, sharing space with other names, never with marks, doors or the legend (the first `fixed` entries). */
static int room_label(RE0Box room,float w,float h,RE0Box clip,const RE0Box *used,unsigned n,unsigned fixed,RE0Box *out) {
 if(re0_place_label(room,w,h,clip,used,n,out))return 1;
 if(room.r<=clip.l||room.l>=clip.r||room.b<=clip.t||room.t>=clip.b)return 0;
 static const signed char dirs[8][2]={{1,0},{-1,0},{0,1},{0,-1},{1,1},{-1,1},{1,-1},{-1,-1}};
 for(unsigned pass=0;pass<2;pass++) {
  const unsigned count=pass?fixed:n;
  if(pass&&re0_place_label(room,w,h,clip,used,count,out))return 1;
  for(int ring=1;ring<=8;ring++)for(unsigned d=0;d<8;d++) {
   const float dx=(float)(dirs[d][0]*ring)*(w*.5f+4),dy=(float)(dirs[d][1]*ring)*(h+3);
   const RE0Box c={(room.l+room.r)*.5f+dx-1,(room.t+room.b)*.5f+dy-1,(room.l+room.r)*.5f+dx+1,(room.t+room.b)*.5f+dy+1};
   if(re0_place_label(c,w,h,clip,used,count,out))return 1;
  }
 }
 return 0;
}
int re0_layout_view(const unsigned char *room_seen,const RE0Box *room_box,RE0View *out) {
 int best=-1;float area=0;
 for(unsigned i=0;i<ROOM_COUNT;i++)if(room_seen[i]) {
  const RE0Box c=piece_canvas[i];const float a=(c.r-c.l)*(c.b-c.t);
  if(a>area){area=a;best=(int)i;}
 }
 if(best<0)return 0;
 const RE0Box c=piece_canvas[best],b=room_box[best];const float sx=(b.r-b.l)/(c.r-c.l),sy=(b.b-b.t)/(c.b-c.t),d=sx-sy;
 if(sx<=0||d>sx*.02f||d<-sx*.02f)return 0;
 const float ox=b.l-c.l*sx,oy=b.t-c.t*sx;
 for(unsigned i=0;i<ROOM_COUNT;i++)if(room_seen[i]&&piece_canvas[i].r>piece_canvas[i].l) {
  const float e[4]={room_box[i].l-(piece_canvas[i].l*sx+ox),room_box[i].t-(piece_canvas[i].t*sx+oy),room_box[i].r-(piece_canvas[i].r*sx+ox),room_box[i].b-(piece_canvas[i].b*sx+oy)};
  for(unsigned j=0;j<4;j++)if(e[j]>4||e[j]<-4)return 0;
 }
 *out=(RE0View){sx,ox,oy};return 1;
}
/* RE2 rule: fixed names, inside the room or at a leader's end; a resized name grows away from that end. */
static unsigned layout_ops(const RE0Settings *s,const RE0View *v,float screen,int markers,const unsigned *flags,RE0Box clip,RE0Box legend,RE0Box readout,const unsigned char *room_on,RE0Box *used,unsigned n_used,List *l,RE0PlaceResult *results,unsigned *n_results) {
 const float z=zoom_name(v,screen),k=screen*ROOM_NAME_K*NAME_SCALE*z*(float)s->size/100.0f,bk=k*.6f;const unsigned alpha=(unsigned)(s->opacity*255/100)<<24;
 for(unsigned i=0;i<LAYOUT_COUNT;i++) {
  const RE0RoomLayout *r=&room_layout[i];
  if(r->lang!=(s->english?1u:0u)||!room_on[r->piece])continue;
  const Place *p=&places[r->place];unsigned counts[RE0_CATEGORIES];re0_content_tally(contents+p->first,p->count,(unsigned)s->difficulty,s->mask,flags,counts);
  float bh=0,bw=markers?0:badge_width(counts,bk,&bh);const float nw=s->names?glyphs[r->glyph].w*k:0,nh=s->names?glyphs[r->glyph].h*k:0,w=upper(nw,bw),h=nh+bh;
  const float grow=screen*z/ZOOM_OUT_NAME*(float)s->size/100.0f; /* generated at zoom out, size 100 */
  const float cx=r->leader?r->lx1*v->scale+v->ox+(r->x-r->lx1)*grow:r->x*v->scale+v->ox,cy=r->leader?r->ly1*v->scale+v->oy+(r->y-r->ly1)*grow:r->y*v->scale+v->oy;
  const RE0Box b={cx-w*.5f,cy-h*.5f,cx+w*.5f,cy+h*.5f};/* Zoom can bring a fixed name onto the legend, which stays readable. */
  const int on_legend=boxes_hit(b,legend)||boxes_hit(b,readout),placed=w>0&&!on_legend&&b.r>clip.l&&b.l<clip.r&&b.b>clip.t&&b.t<clip.b;
  if(results&&n_results) {RE0PlaceResult *o=&results[(*n_results)++];o->place=(int)r->place;o->placed=placed;o->box=b;memcpy(o->counts,counts,sizeof(counts));}
  if(!placed)continue;
  if(r->leader&&s->names) {
   const float x0=r->lx0*v->scale+v->ox,y0=r->ly0*v->scale+v->oy,x1=r->lx1*v->scale+v->ox,y1=r->ly1*v->scale+v->oy,t=upper(1,screen*.75f);
   for(int pass=0;pass<2;pass++) {const float e=(pass?t:t+screen*1.5f)*.5f;add(l,lower(x0,x1)-e,lower(y0,y1)-e,upper(x0,x1)+e,upper(y0,y1)+e,pass?alpha|0xf8f0c8u:alpha|0x080808u,-1);}
  }
  if(s->names)add(l,cx-nw*.5f,b.t,cx+nw*.5f,b.t+nh,alpha|0xf8f0c8u,(int)r->glyph);
  float x=cx-bw*.5f;const float top=b.t+nh;
  if(bw>0)for(unsigned c=0;c<RE0_CATEGORIES;c++)if(counts[c]) {
   unsigned dg=digit_ids[counts[c]>9?9:counts[c]],a=badge_ids[c],color=alpha|(category_color[c]&0xffffffu);
   add(l,x,top,x+glyphs[a].w*bk,top+glyphs[a].h*bk,color,(int)a);x+=glyphs[a].w*bk;
   add(l,x,top,x+glyphs[dg].w*bk,top+glyphs[dg].h*bk,color,(int)dg);x+=glyphs[dg].w*bk;
  }
  (void)used; /* RE2 Remake style: room names are drawn first and nothing avoids them */
 }
 return n_used;
}
static unsigned room_ops(const RE0Settings *s,const Shown *shown,float screen,int markers,const unsigned *flags,RE0Box clip,RE0Box *used,unsigned n_used,List *l,RE0PlaceResult *results,unsigned *n_results) {
 const float k=screen*ROOM_NAME_K*NAME_SCALE*(float)s->size/100.0f,bk=k*.6f;const unsigned alpha=(unsigned)(s->opacity*255/100)<<24;const unsigned fixed=n_used;
 /* Small rooms choose first: they have nowhere else to go, large rooms can absorb a shifted label. */
 unsigned order[PLACE_COUNT],count=0;
 for(unsigned i=0;i<PLACE_COUNT;i++)if(shown->seen[i]) {
  float a=(shown->box[i].r-shown->box[i].l)*(shown->box[i].b-shown->box[i].t);unsigned j=count++;
  while(j&&(shown->box[order[j-1]].r-shown->box[order[j-1]].l)*(shown->box[order[j-1]].b-shown->box[order[j-1]].t)>a){order[j]=order[j-1];j--;}
  order[j]=i;
 }
 for(unsigned o=0;o<count;o++) {
  unsigned i=order[o],counts[RE0_CATEGORIES];const Place *p=&places[i];const unsigned g=s->english?p->en:p->ko;
  re0_content_tally(contents+p->first,p->count,(unsigned)s->difficulty,s->mask,flags,counts);
  float bh=0,bw=markers?0:badge_width(counts,bk,&bh);const float nw=s->names?glyphs[g].w*k:0,nh=s->names?glyphs[g].h*k:0,w=upper(nw,bw),h=nh+bh;
  RE0Box b={0,0,0,0};int placed=w>0&&n_used<MAX_RESERVED&&room_label(shown->box[i],w,h,clip,used,n_used,fixed,&b);
  if(results&&n_results) {RE0PlaceResult *r=&results[(*n_results)++];r->place=(int)i;r->placed=placed;r->box=b;memcpy(r->counts,counts,sizeof(counts));}
  if(!placed)continue;
  const float cx=(b.l+b.r)*.5f;
  leader_ops(&b,&shown->box[i],screen,alpha,l);
  if(s->names)add(l,cx-nw*.5f,b.t,cx+nw*.5f,b.t+nh,alpha|0xf8f0c8u,(int)g);
  float x=cx-bw*.5f;const float top=b.t+nh;
  if(bw>0)for(unsigned c=0;c<RE0_CATEGORIES;c++)if(counts[c]) {
   unsigned d=digit_ids[counts[c]>9?9:counts[c]],a=badge_ids[c],color=alpha|(category_color[c]&0xffffffu);
   add(l,x,top,x+glyphs[a].w*bk,top+glyphs[a].h*bk,color,(int)a);x+=glyphs[a].w*bk;
   add(l,x,top,x+glyphs[d].w*bk,top+glyphs[d].h*bk,color,(int)d);x+=glyphs[d].w*bk;
  }
  used[n_used++]=b;
 }
 return n_used;
}
int re0_frame_marker_done(unsigned index,const unsigned *flags,RE0ArrangeView *arrange){return index<MARKER_COUNT&&re0_marker_state_done(&marker_state[index],flags,arrange);}
static int marker_room_on(const RE0MarkerDef *m,const unsigned char *room_on) {
 if(!m->rooms)return room_on[m->piece];
 for(unsigned i=0;i<m->rooms;i++)if(room_on[marker_rooms[m->first_room+i]])return 1;
 return 0;
}
int re0_frame_marker_on(unsigned index,const RE0Settings *s,const unsigned char *room_drawn,const unsigned *flags) {
 unsigned char on[ROOM_COUNT];
 if(index>=MARKER_COUNT||!s||!room_drawn)return 0;
 scope_rooms(s,flags,room_drawn,on);return marker_room_on(&markers[index],on);
}
static int marker_visible(const RE0MarkerDef *m,const RE0Settings *s,const unsigned char *room_on,const unsigned char *off,const unsigned *flags,RE0ArrangeView *arrange,unsigned index) {
 const unsigned need=marker_state[index].need; /* an event's own precondition, read from its script: it cannot have run or be next until then */
 if(need!=0xffff&&(!flags||!flag_set(flags,need)))return 0;
 return !re0_marker_state_done(&marker_state[index],flags,arrange)&&re0_condition_met(m->condition,flags)&&marker_room_on(m,room_on)&&(m->modes>>s->difficulty&1)&&(s->mask>>m->category&1)&&!(off&&off[index]);
}
/* Priority, as RE2 docs/DEVELOPMENT.md: key items and puzzles are never covered; locks and documents next; common items and enemies may be covered or hidden. */
enum {CAT_LOCK,CAT_KEY,CAT_FILE,CAT_PUZZLE,CAT_ITEM,CAT_ENEMY,CAT_EVENT};
static int top_tier(unsigned c){return c==CAT_KEY||c==CAT_PUZZLE||c==CAT_EVENT;}
static int diamond(unsigned c){return c==CAT_PUZZLE||c==CAT_EVENT;}
static int common(unsigned c){return c==CAT_ITEM||c==CAT_ENEMY;}
/* Used only when captured boxes disagree with the static ones, so fixed names are unavailable. */
/* User 2026-11-05: key items and the keys on locks, 10% larger. */
/* User 2026-11-06: enemies are not enlarged. Keys on doors are 120%, then 80% of that (user review of 46), of the size above zoomed out and 150% zoomed in; every other icon is 100% zoomed out and 130% zoomed in; the curve is the name zoom's, t. */
static float icon_gain(unsigned category,float t){return category==CAT_ENEMY?1.0f:ICON_SIZE_BASE*(category==CAT_LOCK?.8f*1.2f+(1.5f-.8f*1.2f)*t:1.0f+.3f*t);}
static float mark_side(unsigned category,float is,float t){return is*icon_gain(category,t)*(category==CAT_KEY||category==CAT_LOCK?1.1f:1.0f);}
static unsigned reserve_marks(const RE0Settings *s,const RE0View *view,const unsigned char *room_on,const unsigned char *off,const unsigned *flags,RE0ArrangeView *arrange,float height,RE0Box *used,unsigned n) {
 const float is=ICON_SIDE*(float)s->icon_size/100.0f*(height/720.0f)*zoom_name(view,height/720.0f);
 for(unsigned i=0;i<MARKER_COUNT&&n<MAX_RESERVED;i++)if(!common(markers[i].category)&&marker_visible(&markers[i],s,room_on,off,flags,arrange,i)) {
  const float x=markers[i].x*view->scale+view->ox,y=markers[i].y*view->scale+view->oy;
  const float side=mark_side(markers[i].category,is,zoom_t(view,height/720.0f));used[n++]=(RE0Box){x-side*.5f,y-side*.5f,x+side*.5f,y+side*.5f};
 }
 return n;
}
typedef struct {RE0Box box;unsigned weight;} Occupied;
static float overlap_score(RE0Box b,const Occupied *o,unsigned n,unsigned min_weight) {
 float s=0;
 for(unsigned i=0;i<n;i++)if(o[i].weight>=min_weight) {
  const float w=lower(b.r,o[i].box.r)-upper(b.l,o[i].box.l),h=lower(b.b,o[i].box.b)-upper(b.t,o[i].box.t);
  if(w>0&&h>0)s+=w*h*(float)o[i].weight;
 }
 return s;
}
/* A name touches its mark, no gap: right, left, below, above, then below or above running from the mark's edge. */
static void name_candidates(RE0Box m,float w,float h,RE0Box out[8]) {
 const float cx=(m.l+m.r)*.5f,cy=(m.t+m.b)*.5f,x[8]={m.r,m.l-w,cx-w*.5f,cx-w*.5f,m.l,m.r-w,m.l,m.r-w},y[8]={cy-h*.5f,cy-h*.5f,m.b,m.t-h,m.b,m.b,m.t-h,m.t-h};
 for(unsigned i=0;i<8;i++)out[i]=(RE0Box){x[i],y[i],x[i]+w,y[i]+h};
}
/* A map name is one or two atlas lines; the tile margin overlaps between them. */
static void name_size(unsigned i,const RE0Settings *s,float k,float *w,float *h) {
 const RE0MarkerDef *d=&markers[i];const Glyph *a=&glyphs[s->english?d->en:d->ko];const unsigned b=marker_line2[i*2u+(s->english?1u:0u)];
 *w=a->w*k;*h=a->h*k;
 if(b!=NO_LINE){*w=upper(*w,glyphs[b].w*k);*h+=(glyphs[b].h-10)*k;}
}
/* Follows the icon's side: 0 icon left, left-aligned; 1 icon right, right-aligned; otherwise centred. */
static void name_ops(unsigned i,const RE0Settings *s,float k,RE0Box n,unsigned slot,unsigned color,List *l) {
 const RE0MarkerDef *d=&markers[i];const Glyph *a=&glyphs[s->english?d->en:d->ko];const unsigned g=s->english?d->en:d->ko,b=marker_line2[i*2u+(s->english?1u:0u)];
 if(b==NO_LINE){add(l,n.l,n.t,n.r,n.b,color,(int)g);return;}
 const float w1=a->w*k,h1=a->h*k,w2=glyphs[b].w*k,w=n.r-n.l,x1=slot==0?n.l:slot==1?n.r-w1:n.l+(w-w1)*.5f,x2=slot==0?n.l:slot==1?n.r-w2:n.l+(w-w2)*.5f;
 add(l,x1,n.t,x1+w1,n.t+h1,color,(int)g);add(l,x2,n.b-glyphs[b].h*k,x2+w2,n.b,color,(int)b);
}
/* The map screen's frame, GUI 1280x720, measured from the live shot at 2560x1440 (art edges; its sprites are not all captured by the hook). The overlay draws at Present, after the frame, so what is under it is not drawn. */
/* Opaque parts only; the list-closed bottom is see-through (live shot). Last box: the item list, only while open. */
static const RE0Box chrome_gui[RE0_CHROME_BOXES]={{176,0,473,112},{176,112,461,138},{198,138,282,177},{848,0,1119,205},{925,205,1119,263},{0,448,192,720},{1088,448,1280,720},{192,538,230,582},{1050,538,1088,634},{192,662,422,720},{858,662,1088,720},{192,470,1088,720}};
static int chrome_on;static unsigned chrome_n;static RE0Box chrome[RE0_CHROME_BOXES];
static int hits_chrome(RE0Box b,RE0Box c){const float mx=lower(slack,(c.r-c.l)*.5f),my=lower(slack,(c.b-c.t)*.5f);return boxes_hit(b,(RE0Box){c.l+mx,c.t+my,c.r-mx,c.b-my});}
static int on_chrome(RE0Box b){for(unsigned j=0;j<chrome_n;j++)if(hits_chrome(b,chrome[j]))return 1;return 0;}
void re0_frame_set_chrome(int shown,float sx,float sy,float ox,float oy) {
 chrome_on=shown;chrome_n=shown==2?RE0_CHROME_BOXES:shown?RE0_CHROME_BOXES-1:0; /* 0 hidden, 1 shown, 2 shown with the item list open */
 for(unsigned i=0;i<RE0_CHROME_BOXES;i++)chrome[i]=(RE0Box){chrome_gui[i].l*sx+ox,chrome_gui[i].t*sy+oy,chrome_gui[i].r*sx+ox,chrome_gui[i].b*sy+oy};
}
const RE0Box *re0_frame_chrome(void){return chrome;}
static int better(float a,float least){return least<0||a<least;}
static unsigned icon_alpha;
static void mark_op(unsigned index,RE0Box m,List *l) {
 const RE0MarkerDef *d=&markers[index];const unsigned c=category_color[d->category];
 /* User 2026-11-05: puzzle orange diamond with !, event purple diamond with ?. The diamond's corners need more room than the square mark. */
 if(diamond(d->category)) {const float e=(m.r-m.l)/9.0f;add(l,m.l-e,m.t-e,m.r+e,m.b+e,(c&0xffffffu)|icon_alpha,d->category==CAT_EVENT?EVENT_MARK_ID:PUZZLE_MARK_ID);return;}
 add(l,m.l,m.t,m.r,m.b,icon_alpha|0xffffffu,(int)marker_icon_glyphs[index]);
}
/* Items the player dropped: slots past the table's rows (native 0x4de500), kind 0x71, room in slot +0x2c, -1 when freed with its bytes left behind (0x412060). Rows are read each frame, so a picked-up item goes on the next. Saved slots end at 0x3e8. */
#define DROP_ICON_ALPHA 0xa6000000u /* 65% */
enum {DROP_FIRST=0x30,DROP_LINK=0x2c,DROP_STEP=0x5c,DROP_END=0x3e8,DROP_KIND=0x71,MAX_DROPS=64};
static RE0DropStats drop_stats;
const RE0DropStats *re0_frame_drop_stats(void){return &drop_stats;}
/* 0x5b3eff-0x5b3f83, as tools/extract/placements.py: nearest piece of the room, over its floors; a point off the piece comes to its edge. */
static int drop_project(unsigned room,float wx,float wy,float wz,const unsigned char *room_on,unsigned *piece,float *cx,float *cy) {
 float least=-1;
 for(unsigned i=drop_proj_first[room];i<drop_proj_first[room+1];i++) {
  const RE0Box b=piece_canvas[drop_proj[i].piece];if(b.r<=b.l||!room_on[drop_proj[i].piece])continue; /* only what this floor draws: a room on two floors has a base for each, and nothing here says which floor the item is on */
  const float x=(drop_proj[i].bx+wx*.07f)*1.5f+163.0f,y=(drop_proj[i].by+wz*.07f)*1.5f-357.0f,dx=upper(upper(b.l-x,0),x-b.r),dy=upper(upper(b.t-y,0),y-b.b),d=dx*dx+dy*dy;
  if(d>400.0f||(drop_proj[i].level==1&&wy>=drop_proj[i].split)||(drop_proj[i].level==2&&wy<drop_proj[i].split))continue; /* 20 canvas px: table rows overshoot up to 16; further is another floor's base */
  if(least<0||d<least){least=d;*piece=drop_proj[i].piece;*cx=lower(upper(x,b.l),b.r);*cy=lower(upper(y,b.t),b.b);}
 }
 return least>=0;
}
static void drop_name(const RE0Settings *s,const unsigned short *row,unsigned amount,float k,RE0Box m,unsigned color,Occupied *occ,unsigned *no,List *l) {
 const unsigned lang=s->english?2u:0u,g=row[lang],g2=row[lang+1],count=row[6];
 if(g==NO_LINE)return;
 unsigned digits[8],nd=0;float w2=0;const float h1=glyphs[g].h*k;float h=h1;
 if(count&&amount>1&&amount<65535) { /* as marker_label */
  unsigned v=count==2?(amount+2)/3:amount;
  do{digits[nd++]=digit_ids[v%10];v/=10;}while(v&&nd<6);
  if(count==2)w2+=(glyphs[DROP_PCT].w-10)*k;else w2+=(glyphs[DROP_MULT].w-10)*k;
  for(unsigned i=0;i<nd;i++)w2+=(glyphs[digits[i]].w-10)*k;
  w2+=10*k;h+=(glyphs[digit_ids[0]].h-10)*k;
 } else if(g2!=NO_LINE){w2=glyphs[g2].w*k;h+=(glyphs[g2].h-10)*k;}
 const float w1=glyphs[g].w*k,w=upper(w1,w2);RE0Box c[8];name_candidates(m,w,h,c);int best=-1;float least=0;
 for(unsigned j=0;j<8;j++) {
  if(c[j].l<reach.l||c[j].t<reach.t||c[j].r>reach.r||c[j].b>reach.b)continue;
  const float a=overlap_score(c[j],occ,*no,1);
  if(best<0||a<least){best=(int)j;least=a;}
 }
 if(best<0||on_chrome(c[best]))return;
 const RE0Box n=c[best];occ[(*no)++]=(Occupied){n,2u};
 const float x1=best==0?n.l:best==1?n.r-w1:n.l+(w-w1)*.5f;add(l,x1,n.t,x1+w1,n.t+h1,color,(int)g);
 if(w2<=0)return;
 float x=best==0?n.l:best==1?n.r-w2:n.l+(w-w2)*.5f;
 if(nd) {
  const float top=n.b-glyphs[digit_ids[0]].h*k;
  if(count==1){const float gw=glyphs[DROP_MULT].w*k;add(l,x,n.b-glyphs[DROP_MULT].h*k,x+gw,n.b,color,DROP_MULT);x+=gw-10*k;}
  while(nd){const unsigned d=digits[--nd];const float gw=glyphs[d].w*k;add(l,x,top,x+gw,n.b,color,(int)d);x+=gw-10*k;}
  if(count==2){const float gw=glyphs[DROP_PCT].w*k;add(l,x,n.b-glyphs[DROP_PCT].h*k,x+gw,n.b,color,DROP_PCT);}
 } else add(l,x,n.b-glyphs[g2].h*k,x+w2,n.b,color,(int)g2);
}
static void drop_ops(const RE0Settings *s,const RE0View *view,const unsigned char *room_on,const RE0ArrangeView *arrange,float is,float k,float height,unsigned alpha,const RE0Box *legend,Occupied *occ,unsigned *no,List *l) {
 typedef struct {const unsigned short *row;unsigned amount;RE0Box m;unsigned cat;} DropName;static DropName names[MAX_DROPS];unsigned named=0;
 memset(&drop_stats,0,sizeof(drop_stats));
 if(!arrange||!arrange->rows||arrange->count>DROP_END)return;
 for(unsigned slot=arrange->count;slot<DROP_END;slot++) {
  unsigned link,kind,item,amount;float pos[3];const unsigned char *row=arrange->rows+DROP_FIRST+slot*DROP_STEP;
  memcpy(&link,arrange->rows+DROP_LINK+slot*DROP_STEP,4);memcpy(&kind,row+4,4);
  if(link==0xffffffffu||kind!=DROP_KIND)continue;
  memcpy(&item,row+8,4);memcpy(&amount,row+0x3c,4);memcpy(pos,row+0x20,12);
  if(link>=DROP_ROOMS||!(pos[0]>-100000.0f&&pos[0]<100000.0f&&pos[2]>-100000.0f&&pos[2]<100000.0f)){drop_stats.rejected++;continue;}
  drop_stats.valid++;
  if(drop_stats.valid>MAX_DROPS){drop_stats.capped++;continue;}
  const unsigned short *t=item<DROP_ITEMS?&drop_items[item*7u]:0;
  const unsigned icon=t?t[4]:NO_ICON,cat=t?t[5]:CAT_ITEM;
  if(icon==NO_ICON){drop_stats.unmapped++;drop_stats.last_unmapped=item;}
  if(!(s->mask>>cat&1))continue;
  unsigned piece=0;float cx=0,cy=0;
  if(!drop_project(link,pos[0],pos[1],pos[2],room_on,&piece,&cx,&cy))continue; /* not on this floor */
  /* User: on the game's own coloured dot, centred, see-through so its colour and blink stay visible. */
  const float side=mark_side(cat,is,zoom_t(view,height/720.0f)),x=cx*view->scale+view->ox,y=cy*view->scale+view->oy;
  if(map_known&&(x-side*.5f<reach.l||x+side*.5f>reach.r||y-side*.5f<reach.t||y+side*.5f>reach.b))continue;
  if(x+side*.5f<area.l||x-side*.5f>area.r||y+side*.5f<area.t||y-side*.5f>area.b)continue;
  const RE0Box m={x-side*.5f,y-side*.5f,x+side*.5f,y+side*.5f};
  if(boxes_hit(m,legend[0])||boxes_hit(m,legend[1])||(chrome_on&&on_chrome(m)))continue;
  add(l,m.l,m.t,m.r,m.b,((unsigned)(((DROP_ICON_ALPHA>>24)*(icon_alpha>>24))/255u)<<24)|(icon==NO_ICON?0xa0a0a0u:0xffffffu),icon==NO_ICON?-1:(int)icon);drop_stats.drawn++;
  occ[(*no)++]=(Occupied){m,1u};
  if(s->item_names&&!(s->item_names==2&&common(cat))&&t&&named<MAX_DROPS)names[named++]=(DropName){t,amount,m,cat};
 }
 /* Icons, then names. Live, candidates 36-38 had right ops but no names; with this order names were seen on candidate 40. Cause not proven. */
 for(unsigned i=0;i<named;i++)drop_name(s,names[i].row,names[i].amount,k,names[i].m,alpha|(category_color[names[i].cat]&0xffffffu),occ,no,l);
}
static void marker_ops(const RE0Settings *s,const RE0View *view,const unsigned char *room_on,const unsigned char *off,const unsigned *flags,RE0ArrangeView *arrange,float height,const RE0Box *used,unsigned n_obstacles,unsigned hard_end,unsigned n,List *l) {
 static unsigned short shown[MARKER_COUNT+1];static RE0Box mark[MARKER_COUNT+1],name[MARKER_COUNT+1];static unsigned char state[MARKER_COUNT+1],slot[MARKER_COUNT+1],ringed[MARKER_COUNT+1];static Occupied occ[MAX_RESERVED+2*MARKER_COUNT+2*MAX_DROPS];
 enum {DROP=0,KEEP=1,NAMED=2};
 const float screen=height/720.0f,t=zoom_t(view,screen),is=ICON_SIDE*(float)s->icon_size/100.0f*screen*zoom_name(view,screen),k=screen*ITEM_NAME_K*NAME_SCALE*zoom_name(view,screen)*(float)s->size/100.0f;const unsigned alpha=(unsigned)(s->opacity*255/100)<<24;
 unsigned count=0,no=0,dup=0;
 /* Weights while names choose: key marks, puzzle marks and the legend 8x, room names 4x, everything else 1x. */
 for(unsigned i=0;i<n;i++)occ[no++]=(Occupied){used[i],i<n_obstacles?1u:i<hard_end?8u:4u};
 for(unsigned i=0;i<MARKER_COUNT;i++)if(marker_visible(&markers[i],s,room_on,off,flags,arrange,i)) {
  const float x=markers[i].x*view->scale+view->ox,y=markers[i].y*view->scale+view->oy;
  const float side=mark_side(markers[i].category,is,t);
  if(map_known&&(x-side*.5f<reach.l||x+side*.5f>reach.r||y-side*.5f<reach.t||y+side*.5f>reach.b))continue;
  if(x+side*.5f<area.l||x-side*.5f>area.r||y+side*.5f<area.t||y-side*.5f>area.b)continue; /* off the map when zoomed: a name pulled back would leave its mark */
  const RE0Box at={x-side*.5f,y-side*.5f,x+side*.5f,y+side*.5f};
  const float grow=diamond(markers[i].category)?side/9.0f:0; /* the diamond's corners reach past its square (mark_op) */
  const RE0Box seen_box={at.l-grow,at.t-grow,at.r+grow,at.b+grow};
  if(map_known&&(seen_box.l<reach.l||seen_box.r>reach.r||seen_box.t<reach.t||seen_box.b>reach.b))continue;
  if(boxes_hit(seen_box,used[n_obstacles])||boxes_hit(seen_box,used[n_obstacles+1]))continue; /* under the legend or the readouts when zoomed */
  /* Same name at the same spot is one pickup listed twice in the table (kinds 0x71 and 0x78); each row still decides for itself whether it is visible. */
  dup=0;for(unsigned j=0;j<count&&!dup;j++)dup=markers[shown[j]].category==markers[i].category&&markers[shown[j]].ko==markers[i].ko&&marker_line2[shown[j]*2u]==marker_line2[i*2u]&&((markers[shown[j]].x==markers[i].x&&markers[shown[j]].y==markers[i].y)||(markers[i].category!=CAT_ENEMY&&!markers[shown[j]].condition!=!markers[i].condition&&markers[shown[j]].x-markers[i].x<4&&markers[i].x-markers[shown[j]].x<4&&markers[shown[j]].y-markers[i].y<4&&markers[i].y-markers[shown[j]].y<4)); /* the conditional table row and its script twin can differ by a few px: Keycard pl-b7, Book of Good sh-2f */
  if(dup)continue;
  shown[count]=(unsigned short)i;mark[count]=at;state[count]=KEEP;
  occ[no++]=(Occupied){mark[count],top_tier(markers[i].category)?8u:1u};count++;
 }
 const unsigned marks_end=no;
 /* User: an event on a key item or a puzzle stands beside it, so both can be seen. */
 for(unsigned i=0;i<count;i++)if(markers[shown[i]].event)for(unsigned j=0;j<count;j++)if((markers[shown[j]].category==CAT_KEY||(markers[shown[j]].category==CAT_PUZZLE&&!markers[shown[j]].event))&&boxes_hit(mark[i],mark[j])) {
  const float ew=mark[i].r-mark[i].l,left=mark[j].r+ew<=area.r?mark[j].r:mark[j].l-ew;mark[i]=(RE0Box){left,mark[j].t,left+ew,mark[j].b};occ[marks_end-count+i].box=mark[i];break;
 }
 /* Names by tier: key items, puzzles, then locks and documents. */
 static const unsigned char tiers[4]={CAT_KEY,CAT_PUZZLE,CAT_LOCK,CAT_FILE};
 icon_alpha=(unsigned)(clamp(s->icon_opacity,10,100)*255/100)<<24;
 if(s->item_names)for(unsigned t=0;t<4;t++)for(unsigned i=0;i<count;i++)if(markers[shown[i]].category==tiers[t]&&!markers[shown[i]].event) { /* events show no name */
  float w,h;name_size(shown[i],s,k,&w,&h);RE0Box c[8],best={0,0,0,0};float least=-1;name_candidates(mark[i],w,h,c);
  for(unsigned j=0;j<8;j++) {
   RE0Box b=c[j];
   if(b.l<reach.l+1){b.r+=reach.l+1-b.l;b.l=reach.l+1;}if(b.r>reach.r-1){b.l-=b.r-(reach.r-1);b.r=reach.r-1;}if(b.t<reach.t+1){b.b+=reach.t+1-b.t;b.t=reach.t+1;}if(b.b>reach.b-1){b.t-=b.b-(reach.b-1);b.b=reach.b-1;}
   const float a=overlap_score(b,occ,no,1);
   if(better(a,least)){least=a;best=b;slot[i]=(unsigned char)j;}
   if(a==0)break;
  }
  /* Nothing free close by: a second ring, one name height out, before settling for overlap. Live, 마이크로 필름 A over 필름 사진. */
  ringed[i]=0;
  if(least>0){const RE0Box wide={mark[i].l-h,mark[i].t-h,mark[i].r+h,mark[i].b+h};name_candidates(wide,w,h,c);for(unsigned j=0;j<8&&least>0;j++){const RE0Box b=c[j];if(b.l<area.l+1||b.t<area.t+1||b.r>area.r-1||b.b>area.b-1)continue;const float a=overlap_score(b,occ,no,1);if(better(a,least)){least=a;best=b;slot[i]=(unsigned char)j;ringed[i]=1;}}}
  name[i]=best;state[i]=NAMED;occ[no++]=(Occupied){best,t<2?8u:2u};
 }
 /* A lower-priority icon on a key mark, key name or puzzle mark is not drawn; a lock or document centred on one becomes a badge down and right. */
 /* Decided on the middle of each icon, the mark size before icons: a bigger picture must not hide a row. Touching icons stay, with the higher one painted over. */
 const float core=is*ICON_SIZE_BASE*7.0f/36.0f; /* the picture's mark size before the zoom gain: a bigger picture must not hide a row */
 for(unsigned i=0;i<count;i++)if(!top_tier(markers[shown[i]].category)&&markers[shown[i]].category!=CAT_LOCK) { /* RE2 Remake style: a lock's key stays on its door; a mark there may cover it */
  int covered=0,centred=0;const float cx=(mark[i].l+mark[i].r)*.5f,cy=(mark[i].t+mark[i].b)*.5f;const RE0Box mi={cx-core,cy-core,cx+core,cy+core};
  for(unsigned j=0;j<count;j++)if(top_tier(markers[shown[j]].category)&&!markers[shown[j]].event) { /* an event sits over a mark, it does not displace it */
   const float jx=(mark[j].l+mark[j].r)*.5f,jy=(mark[j].t+mark[j].b)*.5f;
   if(boxes_hit(mi,(RE0Box){jx-core,jy-core,jx+core,jy+core})) {covered=1;const float dx=cx-jx,dy=cy-jy;if(dx>-core&&dx<core&&dy>-core&&dy<core)centred=1;}
   if(state[j]==NAMED&&!ringed[j]&&markers[shown[j]].category==CAT_KEY&&boxes_hit(mi,name[j]))covered=1; /* a name moved out to find space does not hide a mark */
  }
  if(!covered)continue;
  if(common(markers[shown[i]].category)||!centred){state[i]=DROP;continue;}
  const float d=is*ICON_SIZE_BASE*.6f;mark[i].l+=d;mark[i].r+=d;mark[i].t+=d;mark[i].b+=d;
 }
 /* Common names last: only into space that covers nothing above them, otherwise hidden. Marks of their own tier do not count. */
 if(s->item_names==1)for(unsigned i=0;i<count;i++)if(state[i]==KEEP&&markers[shown[i]].category==CAT_ITEM) { /* User: an enemy's icon replaces its name. */
  float w,h;name_size(shown[i],s,k,&w,&h);RE0Box c[8];name_candidates(mark[i],w,h,c);int best=-1;float least=0;
  for(unsigned j=0;j<8;j++) {
   const RE0Box b=c[j];
   if(b.l<reach.l||b.t<reach.t||b.r>reach.r||b.b>reach.b||overlap_score(b,occ,no,2)>0)continue;
   const float a=overlap_score(b,occ,marks_end,1);
   if(best<0||a<least){best=(int)j;least=a;}
  }
  if(best<0)continue;
  name[i]=c[best];slot[i]=(unsigned char)best;state[i]=NAMED;occ[no++]=(Occupied){c[best],2u};
 }
 /* Painted lowest priority first, so what must never be covered ends on top. */
 for(unsigned pass=0;pass<2;pass++)for(unsigned i=0;i<count;i++) {
  const RE0MarkerDef *d=&markers[shown[i]];
  if(state[i]==DROP||(unsigned)top_tier(d->category)!=pass)continue;
  /* A mark and its name go together: neither stays alone beside the frame. */
  if(chrome_on&&(on_chrome(mark[i])||(state[i]==NAMED&&on_chrome(name[i]))))continue;
  mark_op(shown[i],mark[i],l);
  if(state[i]==NAMED)name_ops(shown[i],s,k,name[i],slot[i],alpha|(category_color[d->category]&0xffffffu),l);
 }
 drop_ops(s,view,room_on,arrange,is,k,height,alpha,&used[n_obstacles],occ,&no,l);
}
unsigned re0_frame_ops(const RE0Settings *s,float width,float height,const unsigned char *room_seen,const RE0Box *room_box,
                       const RE0Box *obstacles,unsigned n_obstacles,const RE0View *view,const unsigned char *marker_off,const unsigned *flags,RE0ArrangeView *arrange,RE0DrawOp *ops,unsigned cap,RE0PlaceResult *results,unsigned *n_results) {
 if(n_results)*n_results=0;
 if(!s||!ops||!room_seen||!room_box||width<=0||height<=0)return 0;
 {RE0Box a=map_known?map_given:(RE0Box){0,0,width,height};if(a.l<0)a.l=0;if(a.t<0)a.t=0;if(a.r>width)a.r=width;if(a.b>height)a.b=height;area=a.r>a.l&&a.b>a.t?a:(RE0Box){0,0,width,height};
  edge_l=hard_known?hard.l:0;edge_r=hard_known?hard.r:width;if(edge_l>area.l)edge_l=area.l;if(edge_r<area.r)edge_r=area.r;
  slack=ICON_SIDE*.5f*(area.b-area.t)/720.0f;reach=(RE0Box){upper(area.l-slack,hard_known?hard.l:0),upper(area.t-slack,hard_known?hard.t:0),lower(area.r+slack,hard_known?hard.r:width),lower(area.b+slack,hard_known?hard.b:height)};
  if(reach.l>area.l)reach.l=area.l;if(reach.t>area.t)reach.t=area.t;if(reach.r<area.r)reach.r=area.r;if(reach.b<area.b)reach.b=area.b;}
 static RE0Box used[MAX_RESERVED],place_box[ROOM_COUNT];static unsigned char room_on[ROOM_COUNT],placed_on[ROOM_COUNT];List l={ops,0,cap};Shown shown;RE0View fixed;
 const int have_fixed=re0_layout_view(room_seen,room_box,&fixed);scope_rooms(s,flags,room_seen,room_on);
 /* A place the game drew keeps its captured box. One it did not draw, lit by All scope, has no box but the static one through the view. */
 for(unsigned i=0;i<ROOM_COUNT;i++) {
  int drawn_here=room_seen[i];
  for(unsigned j=0;j<ROOM_COUNT&&!drawn_here;j++)drawn_here=room_seen[j]&&same_floor(i,j)&&rooms[j].place==rooms[i].place;
  place_box[i]=room_box[i];placed_on[i]=room_on[i]&&room_seen[i];
  if(room_on[i]&&!drawn_here&&have_fixed&&piece_canvas[i].r>piece_canvas[i].l) {
   const RE0Box c=piece_canvas[i];place_box[i]=(RE0Box){c.l*fixed.scale+fixed.ox,c.t*fixed.scale+fixed.oy,c.r*fixed.scale+fixed.ox,c.b*fixed.scale+fixed.oy};placed_on[i]=1;
  }
 }
 merge_places(placed_on,place_box,&shown);
 /* The map's own height scales everything: Original's 4:3 map is as tall as the buffer, a wider display's is not wider in proportion. */
 const float mh=area.b-area.t,screen=mh/720.0f,lk=mh/1440.0f;unsigned n=0;
 for(unsigned i=0;i<n_obstacles&&n<MAX_RESERVED-PLACE_COUNT-2;i++)used[n++]=obstacles[i];
 RE0Box legend=legend_ops(s,lk,&l);
 const unsigned legend_slot=n;used[n++]=legend;
 /* The readouts go with the legend: folded, there is no panel, only an empty slot far off screen. Always right after the legend: marker_ops reads both. */
 const RE0Box readout=s->legend?readout_ops(s,lk,&l):(RE0Box){-1e9f,-1e9f,-1e9f,-1e9f};used[n++]=readout;
 if(chrome_on)for(unsigned i=0;i<chrome_n&&n<MAX_RESERVED;i++)used[n++]=chrome[i];
 /* Held H hides names and everything attached to them; the legend stays, as in RE1 HD. */
 if(s->hidden||!s->enabled)return l.n;
 /* No room panel in Leech Hunter (difficulty 3..7): its contents are the main game's catalogue (user 2026-11-11). */
 if(s->difficulty<=2&&s->selected>=0&&s->selected<PLACE_COUNT&&shown.seen[s->selected])used[n++]=panel_ops(s,&shown,legend.l,legend.t-4,screen*.62f*NAME_SCALE,flags,&l);
 const RE0Box clip=area;
 const unsigned hard_end=n,kept_ops=l.n;
 if(have_fixed)n=layout_ops(s,&fixed,screen,view!=0,flags,clip,legend,readout,room_on,used,n,&l,results,n_results);
 else {
  if(view)n=reserve_marks(s,view,room_on,marker_off,flags,arrange,mh,used,n);
  n=room_ops(s,&shown,screen,view!=0,flags,clip,used,n,&l,results,n_results);
 }
 if(view)marker_ops(s,view,room_on,marker_off,flags,arrange,mh,used,legend_slot,hard_end,n,&l);
 /* Legend and room panel stay on top; everything on the map goes under a shown frame. */
 if(chrome_on) {
  unsigned out=kept_ops;
  for(unsigned i=kept_ops;i<l.n;i++) {
   const RE0Box b={ops[i].l,ops[i].t,ops[i].r,ops[i].b};
   if(!on_chrome(b))ops[out++]=ops[i];
  }
  l.n=out;
 }
 if(!map_known)return l.n;
 /* Reject whole quads: clipping text coordinates would stretch its UVs. */
 unsigned keep=0;
 for(unsigned i=0;i<l.n;i++){const RE0Box w=i<kept_ops?(RE0Box){edge_l,reach.t,edge_r,reach.b}:reach;if(ops[i].l>=w.l&&ops[i].t>=w.t&&ops[i].r<=w.r&&ops[i].b<=w.b)ops[keep++]=ops[i];} /* our own panels reach the display box, the map content only reach */
 return keep;
}

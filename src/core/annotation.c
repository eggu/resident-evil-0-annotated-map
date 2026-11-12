#include <string.h>
#include "annotation.h"
#include <math.h>
static float lower(float a,float b){return a<b?a:b;}
static float upper(float a,float b){return a>b?a:b;}
static int valid(RE0Box b) {
    return isfinite(b.l)&&isfinite(b.t)&&isfinite(b.r)&&isfinite(b.b)&&b.l<b.r&&b.t<b.b;
}
int re0_project_quad(const RE0SpriteQuad *q,const float v[4],RE0Box *out) {
    if(!q||!v||!out) return 0;
    for(unsigned j=0;j<4;j++) if(!isfinite(v[j])) return 0;
    if(v[2]<=0||v[3]<=0) return 0;
    RE0Box b={INFINITY,INFINITY,-INFINITY,-INFINITY};
    for(unsigned i=0;i<4;i++) {
        float x=q->v[i*4]*v[2]+v[0], y=q->v[i*4+1]*v[3]+v[1];
        if(!isfinite(x)||!isfinite(y)||fabsf(x)>131072||fabsf(y)>131072) return 0;
        b.l=lower(b.l,x); b.r=upper(b.r,x); b.t=lower(b.t,y); b.b=upper(b.b,y);
    }
    if(!valid(b)) return 0;
    *out=b; return 1;
}
RE0Box re0_gui_to_backbuffer(RE0Box b,const RE0GameRect *g) {
    b.l+=(float)g->view_l;b.r+=(float)g->view_l;b.t+=(float)g->view_t;b.b+=(float)g->view_t;
    const int blitted=g->target_w>0&&g->target_h>0&&g->target_w==g->render_w&&g->target_h==g->render_h&&(g->target_w!=g->back_w||g->target_h!=g->back_h)&&g->blit_r>g->blit_l&&g->blit_b>g->blit_t;
    if(!blitted) return b;
    const float sx=(float)(g->blit_r-g->blit_l)/(float)g->target_w,sy=(float)(g->blit_b-g->blit_t)/(float)g->target_h;
    return (RE0Box){b.l*sx+(float)g->blit_l,b.t*sy+(float)g->blit_t,b.r*sx+(float)g->blit_l,b.b*sy+(float)g->blit_t};
}
RE0Box re0_map_viewport(const RE0GameRect *g) {
    const RE0Box none={0,0,0,0};
    if(!g) return none;
    const int blitted=g->target_w>0&&g->target_h>0&&g->target_w==g->render_w&&g->target_h==g->render_h&&(g->target_w!=g->back_w||g->target_h!=g->back_h)&&g->blit_r>g->blit_l&&g->blit_b>g->blit_t;
    RE0Box b=blitted?(RE0Box){(float)g->blit_l,(float)g->blit_t,(float)g->blit_r,(float)g->blit_b}:(RE0Box){(float)g->view_l,(float)g->view_t,(float)g->view_r,(float)g->view_b};
    return valid(b)&&b.r-b.l<=131072&&b.b-b.t<=131072?b:none;
}
RE0Box re0_display_area(RE0Box b,int mode) {
    if(mode==1&&valid(b)) {
        const float w=(b.b-b.t)*4.0f/3.0f;
        if(b.r-b.l>w){const float mid=(b.l+b.r)*.5f;b.l=mid-w*.5f;b.r=mid+w*.5f;}
    }
    return b;
}
RE0Box re0_display_bounds(RE0Box b,int mode,RE0Box left,RE0Box right) {
    b=re0_display_area(b,mode);
    /* Only the gradient's nearly opaque outer part is outside the map; its see-through inner band is still map. */
    if(valid(left)){const float cut=left.l+(left.r-left.l)*RE0_GRADIENT_OPAQUE;if(cut>b.l)b.l=cut;}
    if(valid(right)){const float cut=right.r-(right.r-right.l)*RE0_GRADIENT_OPAQUE;if(cut<b.r)b.r=cut;}
    return b;
}
int re0_place_label(RE0Box room,float w,float h,RE0Box clip,const RE0Box *used,unsigned n,RE0Box *out) {
    if(!out||!valid(room)||!valid(clip)||!isfinite(w)||!isfinite(h)||w<=0||h<=0||n>1024||(n&&!used)) return 0;
    if(room.r<=clip.l||room.l>=clip.r||room.b<=clip.t||room.t>=clip.b) return 0;
    float x=(room.l+room.r-w)*.5f, y=(room.t+room.b-h)*.5f;
    const float offsets[7][2]={{0,0},{0,-1},{0,1},{-1,0},{1,0},{0,-2},{0,2}};
    for(unsigned i=0;i<7;i++) {
        float dx=offsets[i][0]*(w+4),dy=offsets[i][1]*(h+3);
        RE0Box b={x+dx,y+dy,x+dx+w,y+dy+h};
        if(b.l<clip.l||b.r>clip.r||b.t<clip.t||b.b>clip.b) continue;
        int hit=0;
        for(unsigned j=0;j<n;j++) if(b.l<used[j].r+2&&b.r>used[j].l-2&&b.t<used[j].b+2&&b.b>used[j].t-2) {hit=1;break;}
        if(!hit) {*out=b;return 1;}
    }
    return 0;
}
int re0_condition_met(unsigned condition,const unsigned *flags) {
    if(!condition) return 1;
    if(!flags||condition>255) return 0;
    const unsigned flag=RE0_FLAG_BASE+condition;
    return (int)(flags[flag>>5]>>(flag&31)&1);
}
static unsigned read_u32(const unsigned char *p){unsigned v;memcpy(&v,p,4);return v;}
static const unsigned table_rows[3]={647,589,568}; /* loctbl0000, 0100, 0200: [mgr+0x24fac] */
enum {ROW_BASE=0x30,ROW_LINK=0x2c,STRIDE=0x5c,KIND=4,ITEM=8,GONE=0x39};
/* Leech Hunter: 0x4111cc loads loctbl030<rand()%5> (263, 263, 264, 264, 264 rows) and keeps the pick at +0x24ff4, which a save restore may not bring back, as with the mode.
 * Told apart by item ids at slots where the tables of one size differ; pickup clears only the kind (0x4de816), so a taken row still votes. tests/test_placements.py checks these against the game. */
static const unsigned short leech_slots[2][8]={{2,3,4,5,6,12,13,17},{52,55,56,77,118,176,185,186}};
static const unsigned short leech_items[5][8]={{90,90,90,91,91,91,91,90},{91,91,91,90,90,90,90,91},{91,90,2,17,4,90,91,43},{43,91,91,53,90,91,108,90},{90,43,90,91,3,34,43,6}};
static unsigned read_row_u32(const RE0ArrangeView *a,unsigned slot,unsigned at){unsigned v;memcpy(&v,a->rows+ROW_BASE+slot*STRIDE+at,4);return v;}
int re0_arrange_difficulty(const RE0ArrangeView *a) {
    if(!a||!a->rows) return -1;
    for(int i=0;i<3;i++)if(a->count==table_rows[i]) return i;
    if(a->count!=263&&a->count!=264) return -1;
    const unsigned group=a->count==264,first=group?2:0,last=group?5:2;int best=-1;unsigned best_votes=0;
    for(unsigned t=first;t<last;t++){
        unsigned votes=0;
        for(unsigned k=0;k<8;k++)votes+=read_row_u32(a,leech_slots[group][k],ITEM)==leech_items[t][k];
        if(votes>best_votes){best_votes=votes;best=(int)t;}
    }
    return best_votes>4?3+best:-1; /* a clear majority, else unknown */
}
int re0_kind_is_enemy(unsigned kind) {return kind>=0x10&&kind<=0x6f&&kind!=0x3b;}
void re0_arrange_note_actor(const RE0ArrangeView *a,unsigned *killed,int slot,int hp) {
    if(!a||!a->rows||!killed||slot<0||(unsigned)slot>=a->count||(unsigned)slot>=RE0_ROW_SLOTS||hp>0) return;
    if(re0_kind_is_enemy(read_u32(a->rows+ROW_BASE+(unsigned)slot*STRIDE+KIND))) killed[(unsigned)slot>>5]|=1u<<((unsigned)slot&31);
}
int re0_marker_state_done(const RE0MarkerState *m,const unsigned *flags,RE0ArrangeView *a) {
    if(!m) return 0;
    if(flags) {
        if(m->flag!=0xffff&&(flags[m->flag>>5]>>(m->flag&31)&1)) return 1;
        if(m->flag2!=0xffff&&(flags[m->flag2>>5]>>(m->flag2&31)&1)) return 1;
    }
    const int table=re0_arrange_difficulty(a);
    if(table<0) return 0;
    const unsigned short slots[8]={m->slot0,m->slot1,m->slot2,m->leech0,m->leech1,m->leech2,m->leech3,m->leech4};
    const unsigned slot=slots[table];
    if(slot==0xffff) return 0;
    const unsigned char *row=a->rows+ROW_BASE+slot*STRIDE;
    const unsigned kind=read_u32(row+KIND);
    if(read_u32(row)!=m->room||(kind&&kind!=m->kind)||(m->item!=0xffff&&read_u32(row+ITEM)!=m->item)){a->mismatches++;return 0;}
    if(kind==0||row[GONE]||read_u32(a->rows+ROW_LINK+slot*STRIDE)==0xffffffffu) return 1;
    return a->killed&&slot<RE0_ROW_SLOTS&&(a->killed[slot>>5]>>(slot&31)&1);
}
unsigned re0_content_count(const RE0Content *row,unsigned mode,unsigned mask,const unsigned *flags) {
    if(!row||mode>2||row->category>=RE0_CATEGORIES||!(mask>>row->category&1)||!re0_condition_met(row->condition,flags)) return 0;
    return mode==0?row->easy:mode==1?row->normal:row->hard;
}
unsigned re0_content_tally(const RE0Content *rows,unsigned n,unsigned mode,unsigned mask,const unsigned *flags,unsigned counts[RE0_CATEGORIES]) {
    unsigned visible=0;
    for(unsigned i=0;i<RE0_CATEGORIES;i++) counts[i]=0;
    if(!rows) return 0;
    for(unsigned i=0;i<n;i++) {
        unsigned c=re0_content_count(&rows[i],mode,mask,flags);
        if(c){counts[rows[i].category]+=c;visible++;}
    }
    return visible;
}

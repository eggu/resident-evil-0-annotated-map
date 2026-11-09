/* Browser entry for the same frame code the ASI links. No logic lives here: fixed buffers and one call. */
#include "../core/frame.h"
#include <string.h>
#define MAX_ROOMS 256
#define MAX_MARKERS 2048
#define MAX_OPS 8192
#define MAX_OBSTACLES 256
void *memset(void *d,int v,size_t n){unsigned char *p=d;while(n--)*p++=(unsigned char)v;return d;}
void *memcpy(void *d,const void *s,size_t n){unsigned char *p=d;const unsigned char *q=s;while(n--)*p++=*q++;return d;}
static RE0Settings settings;static unsigned char seen[MAX_ROOMS],off[MAX_MARKERS];static RE0Box boxes[MAX_ROOMS];static RE0DrawOp ops[MAX_OPS];static RE0Box obstacles[MAX_OBSTACLES],kept[MAX_OBSTACLES];static unsigned flags[RE0_FLAG_WORDS];static unsigned char arrange_rows[0x30+0x4e8*0x5c];static RE0ArrangeView arrange={0,arrange_rows,0,0};
RE0Settings *re0_wasm_settings(void){return &settings;}
unsigned char *re0_wasm_seen(void){return seen;}
unsigned char *re0_wasm_marker_off(void){return off;}
RE0Box *re0_wasm_boxes(void){return boxes;}
RE0DrawOp *re0_wasm_ops(void){return ops;}
RE0Box *re0_wasm_obstacles(void){return obstacles;}
unsigned *re0_wasm_flags(void){return flags;}
unsigned char *re0_wasm_arrange_rows(void){return arrange_rows;}
void re0_wasm_arrange_set(unsigned count){arrange.count=count;}
unsigned re0_wasm_arrange_mismatches(void){return arrange.mismatches;}
int re0_wasm_done(unsigned index){return re0_frame_marker_done(index,flags,&arrange);}
int re0_wasm_met(unsigned condition){return re0_condition_met(condition,flags);}
int re0_wasm_key(int key){return re0_settings_key(&settings,key,seen,flags);}
int re0_wasm_room_state(unsigned index){return re0_frame_room_state(index,flags);}
int re0_wasm_marker_on(unsigned index){return re0_frame_marker_on(index,&settings,seen,flags);}
static unsigned kept_count;
unsigned re0_wasm_kept(void){return kept_count;}
static int frame_on;void re0_wasm_set_frame(int on){frame_on=on;}const void *re0_wasm_chrome(void){re0_frame_set_chrome(frame_on,1.5f,1.5f,0,0);return re0_frame_chrome();}
unsigned re0_wasm_frame(float width,float height,float scale,float ox,float oy,unsigned n_obstacles) {
 re0_frame_set_chrome(frame_on,1.5f,1.5f,0,0);
 RE0View view={scale,ox,oy};kept_count=0;
 /* Offered the way the ASI's capture offers them, so the same sprites are dropped at the same zoom. */
 for(unsigned i=0;i<n_obstacles&&i<MAX_OBSTACLES;i++)if(re0_obstacle_fits(obstacles[i]))kept[kept_count++]=obstacles[i];
 return re0_frame_ops(&settings,width,height,seen,boxes,kept,kept_count,&view,off,flags,&arrange,ops,MAX_OPS,0,0);
}

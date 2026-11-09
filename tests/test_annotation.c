#include "../src/core/annotation.h"
#include <assert.h>
#include <math.h>
int main(void) {
 RE0SpriteQuad q={{0,0,0,0,0,20,0,0,40,20,0,0,40,0,0,0}};
 float v[4]={100,50,2,3}; RE0Box b,p,clip={0,0,400,300};
 assert(re0_project_quad(&q,v,&b)); assert(b.l==100&&b.t==50&&b.r==180&&b.b==110);
 assert(re0_place_label(b,60,20,clip,0,0,&p));
 RE0Box used=p; assert(re0_place_label(b,60,20,clip,&used,1,&p)); assert(p.b<=used.t-2||p.t>=used.b+2);
 assert(!re0_place_label(b,600,20,clip,0,0,&p));
 q.v[0]=NAN; assert(!re0_project_quad(&q,v,&b));
 assert(!re0_place_label((RE0Box){500,0,600,40},20,10,clip,0,0,&p));
 RE0Content rows[3]={{0,1,1,1,0,0,0},{1,2,0,1,0,0,0},{4,0,3,0,0,0,0}};unsigned n[RE0_CATEGORIES];
 assert(re0_content_tally(rows,3,1,63,0,n)==2&&n[0]==1&&n[1]==0&&n[4]==3); /* normal: weapon row absent */
 assert(re0_content_tally(rows,3,0,63,0,n)==2&&n[1]==2&&n[4]==0); /* easy: enemy row absent */
 assert(re0_content_tally(rows,3,1,1,0,n)==1&&n[4]==0); /* enemy filtered out */
 assert(re0_content_count(&rows[0],3,63,0)==0); /* unknown difficulty refuses */
 unsigned flags[RE0_FLAG_WORDS]={0};RE0Content reward={4,1,1,1,0,0,160};
 assert(re0_content_count(&reward,1,63,0)==0&&re0_content_count(&reward,1,63,flags)==0); /* unknown and unset both hide */
 flags[(RE0_FLAG_BASE+160)>>5]|=1u<<((RE0_FLAG_BASE+160)&31);assert(re0_content_count(&reward,1,63,flags)==1&&re0_condition_met(0,0)&&!re0_condition_met(161,flags)&&!re0_condition_met(256,flags));
 RE0Content bad={9,1,1,1,0,0,0};assert(re0_content_count(&bad,1,63,0)==0&&re0_content_tally(0,3,1,63,0,n)==0);
 return 0;
}

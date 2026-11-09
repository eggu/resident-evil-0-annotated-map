#ifndef RE0_ANNOTATION_H
#define RE0_ANNOTATION_H
#include "map_transform.h"
typedef struct { float l,t,r,b; } RE0Box;
/* Render-argument +b8/+bc origin and +c0/+c4 scale, after native parent transforms. */
int re0_project_quad(const RE0SpriteQuad *quad, const float viewport[4], RE0Box *out);
/* Where GUI coordinates land on the back buffer. Native: renderer viewport +bc/+c0 (setter 0x866ac0), bound target +fc/+fe (u16),
 * and sRender's render size +b8/+bc blitted into +a4..+b0 of the back buffer +433e50/54 (centred at 0x72376a for an Aspect that differs from the display). */
typedef struct { int view_l,view_t,target_w,target_h,render_w,render_h,blit_l,blit_t,blit_r,blit_b,back_w,back_h,view_r,view_b; } RE0GameRect; /* view_r/view_b: the viewport setter's rectangle, renderer +0xc4/+0xc8 */
RE0Box re0_gui_to_backbuffer(RE0Box box,const RE0GameRect *rect);
/* Where the game draws its map inside the back buffer, from the game's own rectangle and not the window: the blit rectangle when the render target is blitted (pillarbox or letterbox), else the viewport rectangle. Original (4:3) leaves black bars outside it, Wide fills the buffer. Empty (all 0) when the rectangle is unreadable or empty, then the caller uses the whole buffer. */
RE0Box re0_map_viewport(const RE0GameRect *rect);
/* Native display menu: saved option +20 is 0 Wide, 1 Original. */
/* map_bg01 texture (224 px, DXT5 alpha, black): alpha stays at or above 85% for its outer 79 columns of 224, then falls to 0 at the inner edge (tests/test_display_area.py re-measures it). The sprite is mirrored on the right, so the outer part is always the screen edge. */
#define RE0_GRADIENT_OPAQUE (79.0f/224.0f)
RE0Box re0_display_area(RE0Box viewport,int mode);
RE0Box re0_display_bounds(RE0Box viewport,int mode,RE0Box left,RE0Box right);
/* Keep a label inside its clip, avoid native icons and previously placed labels. */
int re0_place_label(RE0Box room, float width, float height, RE0Box clip,
                    const RE0Box *reserved, unsigned count, RE0Box *out);
#define RE0_CATEGORIES 7 /* locks, key items, files, puzzles, items, enemies, events (ids; the legend lists events after puzzles) */
/* Spawn gate 0x410c46-0x410c75: condition 0 always spawns, others need flag 0x312+condition of the bit array at [0xdcc014]+0x20 (0x59b8d0). */
#define RE0_FLAG_BASE 0x312
#define RE0_FLAG_WORDS ((RE0_FLAG_BASE+256+31)/32)
/* Placement manager [0xdcc010], read each frame. Pickup 0x4de816 zeroes a row's kind and spawn 0x410bf5 refuses kind 0; script ObjDeleteType unlinks a row (link -1).
 * The table is told by its row count: save restore 0x4103e0 brings back rows and count but not the mode field +0x24ff0, which stays 0 after a load.
 * rows null or an unknown count: unknown, nothing counts as done. mismatches counts rows that did not hold the expected room, kind and item.
 * Enemies: 0x412c30 saves an actor into its row when its room unloads (0x61dde0) or at a save (0x613854); its save virtual (vtable+0x94) returns 1 at HP 0, which sets row+0x39 (0x412d7a), and spawn 0x410c02 then refuses the row.
 * Before that only the actor holds the kill: killed is a slot bit set from the actor lists, null when not read. */
#define RE0_ROW_SLOTS 0x4e8
#define RE0_KILLED_WORDS ((RE0_ROW_SLOTS+31)/32)
typedef struct { unsigned count; const unsigned char *rows; unsigned mismatches; const unsigned *killed; } RE0ArrangeView;
/* What finishes a marker: slot per table (0xffff none) or flag, flag2 in the bit array (0xffff none). kind: table kind the row must hold, or 0 once taken. item 0xffff: not guarded, as 0x412c30 rewrites row+8 from the actor. */
typedef struct { unsigned short slot0,slot1,slot2,flag,flag2,item,room,kind,need; } RE0MarkerState;
int re0_marker_state_done(const RE0MarkerState *m,const unsigned *flags,RE0ArrangeView *arrange);
/* The enemy group of the room walk 0x61d544-0x61d54f: 0x10..0x6f without 0x3b (uEnemy3bRebecca, a player stand-in). */
int re0_kind_is_enemy(unsigned kind);
/* One live actor from the lists: sets slot's killed bit when HP is at or below 0 and its table row is an enemy. Item and player actors have HP 0 too, so the row decides. */
void re0_arrange_note_actor(const RE0ArrangeView *arrange,unsigned *killed,int slot,int hp);
/* The game's own difficulty from the table it loaded, 0..2; -1 when unknown or another mode. */
int re0_arrange_difficulty(const RE0ArrangeView *arrange);
/* flags is that array's start; null means unknown, so only condition 0 passes. */
int re0_condition_met(unsigned condition,const unsigned *flags);
/* One listed thing in a place; per-difficulty counts as listed by the catalogue. */
typedef struct { unsigned char category,easy,normal,hard; unsigned short ko,en; unsigned char condition; } RE0Content;
/* Listed count of a row at difficulty 0..2, or 0 when its category is filtered out. */
unsigned re0_content_count(const RE0Content *row, unsigned mode, unsigned mask, const unsigned *flags);
/* Per-category totals for a place; returns how many rows remain visible. */
unsigned re0_content_tally(const RE0Content *rows, unsigned n, unsigned mode, unsigned mask, const unsigned *flags, unsigned counts[RE0_CATEGORIES]);
#endif

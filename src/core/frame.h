#ifndef RE0_FRAME_H
#define RE0_FRAME_H
#include "annotation.h"
/* Everything the overlay shows is decided here; ASI and emulator only paint the resulting list. */
/* scope: [8], which rooms annotations follow. RE0_SCOPE_VISITED: rooms the player entered; REVEALED: those and the rooms of a held map; ALL: every room of a floor the game draws. */
enum {RE0_SCOPE_VISITED,RE0_SCOPE_REVEALED,RE0_SCOPE_ALL};
typedef struct { int enabled,names,english,size,opacity,difficulty; unsigned mask; int selected,hidden,scope,icon_size,icon_opacity,item_names,legend; } RE0Settings;
/* glyph<0 paints a solid rectangle. color is ARGB. */
typedef struct { float l,t,r,b; unsigned color; int glyph; } RE0DrawOp;
/* A located thing on the map, in the map GUI's 1280x720 space. modes: bit 0 easy, 1 normal, 2 hard. */
/* condition: shown when met. rooms: 0 for a mark in a room (piece); otherwise it sits on a door, and marker_rooms[first_room..] are the pieces the game joins to that door. */
typedef struct { float x,y; unsigned short piece,ko,en; unsigned char category,modes,hollow,condition; unsigned short first_room; unsigned char rooms,event; } RE0MarkerDef;
/* Native 0x5bac90: visited when flags visited0 and visited1 are set (0xffff none). Native 0x5b4af4, 0x5b4b6d: revealed when flag revealed0 or revealed1 is. data/room-state.json. */
typedef struct { unsigned short visited0,visited1,revealed0,revealed1; } RE0RoomState;
/* Map canvas to screen. Null means no location markers: rooms show per-category counts instead. */
typedef struct { float scale,ox,oy; } RE0View;
typedef struct { int place,placed; RE0Box box; unsigned counts[RE0_CATEGORIES]; } RE0PlaceResult;
/* A room name fixed at generation (tools/extract/room_layout.py), in map canvas space; names never move at runtime. */
typedef struct { unsigned short piece,place,glyph,lang; float x,y,lx0,ly0,lx1,ly1; int leader; } RE0RoomLayout;
/* Map canvas to screen from captured room boxes against their static boxes. 0 when they disagree: then frame falls back to placing beside the captured boxes. */
float re0_frame_name_zoom(const RE0View *v,float screen);
int re0_layout_view(const unsigned char *room_seen,const RE0Box *room_box,RE0View *out);
/* Which captured non-room sprites names must avoid: small ones, so the map's own large art never counts. */
int re0_obstacle_fits(RE0Box b);
typedef struct {unsigned valid,drawn,unmapped,rejected,capped,last_unmapped;} RE0DropStats;
const RE0DropStats *re0_frame_drop_stats(void);
#define RE0_CHROME_BOXES 12
/* Where the game draws the map inside the back buffer (re0_map_viewport); empty means the whole buffer. Legend, readouts, clipping and name/mark placement use it. re0_frame_map is the rectangle the last frame used. */
void re0_frame_set_map(RE0Box area);
/* The display's own rectangle (Original's 4:3 box), set after re0_frame_set_map each frame: the one edge that never gets slack. */
void re0_frame_set_viewport(RE0Box viewport);
RE0Box re0_frame_map(void);
void re0_frame_set_chrome(int shown,float sx,float sy,float ox,float oy);
const RE0Box *re0_frame_chrome(void);
/* A marker already finished in the game: item taken, puzzle solved, door unlocked, enemy killed. */
int re0_frame_marker_done(unsigned index,const unsigned *flags,RE0ArrangeView *arrange);
/* Native piece state, 0x5b4b18-0x5b4b25, of piece index: bit 0 visited, bit 1 revealed. 0 is a room the game does not draw. */
int re0_frame_room_state(unsigned index,const unsigned *flags);
/* Is marker index's room on under this scope, given the pieces the game drew. flags null means unknown: what was drawn counts. */
int re0_frame_marker_on(unsigned index,const RE0Settings *s,const unsigned char *room_drawn,const unsigned *flags);
unsigned re0_frame_room_count(void);
unsigned re0_frame_place_count(void);
unsigned re0_frame_marker_count(void);
/* Whether the overlay may draw at this Present. Present outpaces map draws, so the last capture is redrawn until it is held back: while the screen fade is up or the map's own state is not live, every capture so far goes stale, and only a capture made after that (a higher generation) draws again. A fast fade that returns to clear before the map is gone therefore draws nothing: no timing is involved. */
typedef struct { unsigned stale; } RE0DrawGate;
int re0_present_gate(RE0DrawGate *gate,unsigned generation,int fade_clear,int map_live);
void re0_settings_default(RE0Settings *s);
/* The INI's name and icon sizes. Files from before candidate 44 have no Version and hold sizes on the old scale (their 110% names and 130% icons are now 100%): those are converted once, and 1 is returned so the caller rewrites the file with Version. A size key that is absent (-1) takes the default. */
#define RE0_SIZE_SCALE_VERSION 44
#define RE0_ITEM_NAMES_VERSION 50
#define RE0_CONTENTS_VERSION 52
#define RE0_SETTINGS_VERSION 52
/* Contents bit mask: bit per category id; bit 6 is events. User 2026-11-08: events are spoilers, off by default. Files below Version 52 have the event bit cleared once (51 had copied it from puzzles); a later choice is kept. */
#define RE0_MASK_ALL 127u
#define RE0_MASK_DEFAULT 63u
unsigned re0_settings_contents(int version,int value);
/* Legend order, user 2026-11-08: [2] locks [3] key items [4] files [5] puzzles [6] events [7] items [8] enemies. Row 0..6 -> category id. */
unsigned re0_legend_category(unsigned row);
/* Category colours, 0xRRGGBB, set from the INI's [Colors]; defaults are the shipped colours. re0_color_parse reads '#RRGGBB' (the '#' optional, trailing space or ';' comment allowed): 1 and *rgb, else 0 and *rgb unchanged. */
void re0_frame_set_color(unsigned category,unsigned rgb);
unsigned re0_frame_color(unsigned category);
void re0_frame_reset_colors(void);
int re0_color_parse(const char *text,unsigned *rgb);
/* Rewrites old INI text so that every key of section [Map] holds the given value, changing nothing else (comments, other sections such as [Colors], key order, line endings); missing keys are added at the end of the section, a missing section at the end. If old has no [Colors] section, tail is appended. Returns the length written, 0 when out is too small. */
unsigned re0_ini_merge(const char *old,unsigned old_n,const char *const *keys,const char *const *values,unsigned nk,const char *tail,char *out,unsigned cap);
int re0_settings_ini_sizes(RE0Settings *s,int version,int name_size,int icon_size);
/* The INI's ItemNames: 0 off, 1 all, 2 all except common items. Before Version 50 it was on/off (on -> 1, off -> 0). */
int re0_settings_item_names(int version,int value);
/* Keys: '0'..'9', '[', ']' opacity, '-', '+' size, ',', '.' room selection, '`' legend fold. H cycles item names 1, 2, 0. Returns 1 when a persisted setting changed. */
int re0_settings_key(RE0Settings *s,int key,const unsigned char *room_seen,const unsigned *flags);
/* room_seen/room_box have one entry per native piece. flags: see re0_condition_met. results may be null. Returns the op count. */
unsigned re0_frame_ops(const RE0Settings *s,float width,float height,const unsigned char *room_seen,const RE0Box *room_box,
                       const RE0Box *obstacles,unsigned n_obstacles,const RE0View *view,const unsigned char *marker_off,const unsigned *flags,RE0ArrangeView *arrange,RE0DrawOp *ops,unsigned cap,RE0PlaceResult *results,unsigned *n_results);
#endif

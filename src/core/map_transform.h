#ifndef RE0_MAP_TRANSFORM_H
#define RE0_MAP_TRANSFORM_H

typedef struct {
    float scale;
    float translate_x;
    float translate_y;
} RE0MapTransform;

/* Native GUI setter values from RE0 2025 map method 0x5b5320, not backbuffer coordinates. */
int re0_map_transform(float progress, float focus_x, float focus_y, RE0MapTransform *out);

typedef struct { float v[16]; } RE0SpriteQuad;
/* Native 0x889300 / 0x892680: TL, BL, BR, TR, each xyz0; column-major matrix. */
int re0_sprite_quad(float width, float height, unsigned anchor, int flip_y,
                    const float matrix[16], RE0SpriteQuad *out);

/* Native 0x8918d0 normal-winding texture coordinates: TL, TR, BL, BR. */
int re0_sprite_uv(const float rect[4], unsigned sampler, float out[8]);

#endif

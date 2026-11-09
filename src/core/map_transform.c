#include "map_transform.h"
#include <math.h>

int re0_map_transform(float progress, float focus_x, float focus_y, RE0MapTransform *out) {
    if (!out || !isfinite(progress) || !isfinite(focus_x) || !isfinite(focus_y) ||
        progress < 0.0f || progress > 1.0f)
        return 0;
    float scale = progress * 2.0f + 1.0f;
    float x = 0.0f, y = 0.0f;
    if (scale != 1.0f) {
        x = (focus_x - 640.0f) * -3.0f * progress;
        y = (focus_y - 360.0f) * -3.0f * progress;
    }
    if (!isfinite(x) || !isfinite(y)) return 0;
    *out = (RE0MapTransform){scale, x, y};
    return 1;
}

int re0_sprite_quad(float width, float height, unsigned anchor, int flip_y,
                    const float matrix[16], RE0SpriteQuad *out) {
    anchor &= 15; /* Native 0x892680 reads only these bits; live sprites carry 0xff5. */
    if (!out || !matrix || !isfinite(width) || !isfinite(height) ||
        width <= 0 || height <= 0 || anchor > 10 || (anchor & 3) == 3 ||
        (anchor & 12) == 12 || (flip_y != 0 && flip_y != 1)) return 0;
    for (int i = 0; i < 16; i++) if (!isfinite(matrix[i])) return 0;
    float left = 0, right = width, top = 0, bottom = height;
    if ((anchor & 3) == 1) { left = width * -0.5f; right = -left; }
    if ((anchor & 3) == 2) { left = -width; right = 0; }
    float vertical = height * (flip_y ? -1.0f : 1.0f);
    if ((anchor & 12) == 0) { top = 0; bottom = vertical; }
    if ((anchor & 12) == 4) { top = vertical * -0.5f; bottom = -top; }
    if ((anchor & 12) == 8) { top = -vertical; bottom = 0; }
    float xs[4] = {left, left, right, right};
    float ys[4] = {top, bottom, bottom, top};
    RE0SpriteQuad quad = {0};
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 3; j++) {
            float value = ys[i] * matrix[4+j] + xs[i] * matrix[j];
            value += 0.0f * matrix[8+j];
            value += matrix[12+j];
            if (!isfinite(value)) return 0;
            quad.v[i*4+j] = value;
        }
    }
    *out = quad;
    return 1;
}

int re0_sprite_uv(const float rect[4], unsigned sampler, float out[8]) {
    if (!rect || !out) return 0;
    for (int i = 0; i < 4; i++) if (!isfinite(rect[i])) return 0;
    float left = rect[0], top = rect[1], right = rect[2], bottom = rect[3];
    if (sampler == 0 || sampler == 1) {
        float dx = left > right ? -0.5f : 0.5f;
        float dy = top > bottom ? -0.5f : 0.5f;
        left += dx; right -= dx; top += dy; bottom -= dy;
    }
    out[0] = left; out[1] = top;
    out[2] = right; out[3] = top;
    out[4] = left; out[5] = bottom;
    out[6] = right; out[7] = bottom;
    return 1;
}

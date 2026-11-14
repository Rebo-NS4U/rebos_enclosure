// Ordered 4x4 screen in logical pixels; shared by surfaces and outlines.
float ditherMask(vec2 pixel, float cellSize) {
    ivec2 p = ivec2(mod(floor(pixel / max(cellSize, 0.5)), 4.0));
    const float bayer[16] = float[16](0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5);
    return step(10.0, bayer[p.y * 4 + p.x]);
}

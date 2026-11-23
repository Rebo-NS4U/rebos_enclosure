#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(binding = 1) uniform sampler2D source;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 labelSize;
} ubuf;

void main() {
    vec4 glyph = texture(source, qt_TexCoord0);
    vec2 pixel = floor(qt_TexCoord0 * ubuf.labelSize);
    // Use the Orbit screen's threshold sequence to break up solid letter strokes.
    float order = fract(dot(pixel, vec2(0.7548776865, 0.5698403120)));
    fragColor = glyph * mix(0.52, 1.0, step(0.25, order)) * ubuf.qt_Opacity;
}

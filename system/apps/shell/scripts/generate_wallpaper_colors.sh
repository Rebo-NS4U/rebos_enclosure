#!/usr/bin/env bash
set -euo pipefail

image_path=${1:?wallpaper image is required}
scheme=${2:-scheme-tonal-spot}
mode=${3:-dark}
matugen_config=${4:?matugen config is required}
output_path=${5:?output path is required}
primary_color=${6:-}
secondary_color=${7:-}
for picked_color in "$primary_color" "$secondary_color"; do
  if [[ -n "$picked_color" && ! "$picked_color" =~ ^#[[:xdigit:]]{6}$ ]]; then
    echo '{"error":"Picked colors must be #RRGGBB"}' >&2
    exit 2
  fi
done
if [[ -n "$primary_color$secondary_color" ]] && ! command -v matugen >/dev/null 2>&1; then
  echo '{"error":"Matugen is required for picked wallpaper colors"}' >&2
  exit 127
fi

# Picked source colors override automatic extraction without an interactive prompt.
# Render to an isolated file so failed or interrupted jobs cannot publish a
# partial palette or report success just because an older cache exists.
if command -v matugen >/dev/null 2>&1; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo '{"error":"python3 is required for atomic Matugen generation"}' >&2
    exit 127
  fi
  mkdir -p "$(dirname "$output_path")"
  work_dir=$(mktemp -d "$(dirname "$output_path")/matugen.XXXXXX")
  trap 'rm -rf "$work_dir"' EXIT
  python3 - "$matugen_config" "$work_dir" <<'PYCONFIG'
import json
from pathlib import Path
import re
import sys
source = Path(sys.argv[1]).resolve()
folder = Path(sys.argv[2]).resolve()
config = source.read_text()
config = re.sub(r'^input_path\s*=\s*"colors.json"$',
                lambda _: 'input_path = ' + json.dumps(str(source.parent / 'colors.json')),
                config, flags=re.M)
config = re.sub(r'^output_path\s*=.*$',
                lambda _: 'output_path = ' + json.dumps(str(folder / 'colors.json')),
                config, flags=re.M)
(folder / 'config.toml').write_text(config)
PYCONFIG
  source_args=(image "$image_path" --prefer "${MATUGEN_PREFER:-saturation}")
  if [[ -n "$primary_color" ]]; then
    source_args=(color hex "$primary_color")
  fi
  if matugen "${source_args[@]}" \
      -c "$work_dir/config.toml" -t "$scheme" -m "$mode" && \
      python3 - "$work_dir/colors.json" "$mode" "$image_path" "$scheme" "$work_dir/config.toml" "$primary_color" "$secondary_color" <<'PYVALIDATE'
import colorsys
import json
import re
import sys
import subprocess
from pathlib import Path
palette = json.loads(Path(sys.argv[1]).read_text())
assert all(key in palette for key in ('background', 'primary', 'overBackground', 'surface'))
assert all(isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value)
           for value in palette.values())
def hsv(color):
    return colorsys.rgb_to_hsv(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))

# Matugen ranks actual image colors. Ignore near-neutral/dark candidates and
# allow distinct analogous through complementary pairings (35–180°).
# Keep the existing single-hue scheme when no suitable second color exists.
secondary = None
primary_hue, primary_saturation, _ = hsv(palette['primary'])
try:
    result = None if sys.argv[7] else subprocess.run(
        ['matugen', 'image', sys.argv[3], '--show-source-colors', '--dry-run'],
        capture_output=True, text=True, check=True, timeout=30)
    candidates = [sys.argv[7]] if sys.argv[7] else re.findall(r'^#[0-9a-fA-F]{6}$', result.stdout, re.M)
    for candidate in candidates:
        hue, saturation, value = hsv(candidate)
        distance = min(abs(hue - primary_hue), 1 - abs(hue - primary_hue)) * 360
        if sys.argv[7] or (primary_saturation >= 0.08 and saturation >= 0.25
                           and value >= 0.25 and 35 <= distance <= 180):
            config_path = Path(sys.argv[5])
            second_path = config_path.parent / 'secondary.json'
            second_config = config_path.parent / 'secondary.toml'
            config = re.sub(r'^output_path\s*=.*$',
                            lambda _: 'output_path = ' + json.dumps(str(second_path)),
                            config_path.read_text(), flags=re.M)
            second_config.write_text(config)
            subprocess.run(['matugen', 'color', 'hex', candidate, '-t', sys.argv[4],
                            '-m', sys.argv[2], '-c', str(second_config)],
                           capture_output=True, check=True, timeout=30)
            secondary = json.loads(second_path.read_text())
            # Copy the full role family so containers and fixed colors agree.
            for key, value in secondary.items():
                if 'Primary' in key or key.startswith('primary'):
                    palette[key.replace('Primary', 'Secondary').replace('primary', 'secondary')] = value
            break
except (subprocess.SubprocessError, OSError, ValueError):
    if sys.argv[7]:
        raise
    secondary = None

# Match the tree's vivid crown in dark mode, preserving a distinct secondary
# hue when one was extracted. Light mode retains Matugen's readable tones.
if sys.argv[2] == 'dark' or sys.argv[6] or sys.argv[7]:
    original_primary = sys.argv[6] or palette['primary']
    for role, shift in (('primary', 0), ('secondary', -0.025), ('tertiary', 0.025)):
        picked = sys.argv[7] if role == 'secondary' else sys.argv[6] if role == 'primary' else ''
        if sys.argv[2] != 'dark' and not picked:
            continue
        source = (sys.argv[7] or secondary['primary']) if role == 'secondary' and secondary else original_primary
        hue, saturation, _ = hsv(source)
        chroma = max(0.62, saturation) if saturation >= 0.08 else 0
        offset = 0 if role == 'secondary' and secondary else shift
        channels = colorsys.hsv_to_rgb((hue + offset) % 1, chroma, 0.9)
        # Explicit picks retain their saturation and brightness, including neutrals.
        if picked:
            channels = [int(picked[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        palette[role] = '#' + ''.join(f'{round(v * 255):02x}' for v in channels)
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                  for v in channels]
        luminance = sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
        palette['over' + role.capitalize()] = '#000000' if luminance > 0.179 else '#ffffff'
    palette['surfaceTint'] = palette['primary']
Path(sys.argv[1]).write_text(json.dumps(palette, indent=2) + '\n')
PYVALIDATE
  then
    mv -f "$work_dir/colors.json" "$output_path"
    rm -rf "$work_dir"
    trap - EXIT
    echo "Generated rebos_shell colors with Matugen."
    exit 0
  fi
  rm -rf "$work_dir"
  trap - EXIT
  if [[ -n "$primary_color$secondary_color" ]]; then
    echo '{"error":"Could not generate the picked palette; keeping previous colors"}' >&2
    exit 1
  fi
  echo "Matugen failed; trying Wallust fallback..." >&2
fi

if ! command -v wallust >/dev/null 2>&1; then
  echo '{"error":"Neither matugen nor wallust is installed"}' >&2
  exit 127
fi
if ! command -v jq >/dev/null 2>&1; then
  echo '{"error":"jq is required for the Wallust palette export"}' >&2
  exit 127
fi

mapfile -t palette < <(
  wallust run --no-config --skip-sequences --skip-templates \
    --print-scheme --palette ansi --style "$mode" --check-contrast "$image_path" \
    | awk '/^#[[:xdigit:]]{6}$/{print toupper($0)}'
)

if (( ${#palette[@]} < 16 )); then
  echo '{"error":"Wallust returned an incomplete wallpaper palette"}' >&2
  exit 1
fi

mkdir -p "$(dirname "$output_path")"
temporary_path=$(mktemp "${output_path}.XXXXXX")
trap 'rm -f "$temporary_path"' EXIT

# Elevated surfaces so chrome is not crushed pure black (hue tracks wallpaper).
jq -n \
  --arg background "${palette[0]}" \
  --arg foreground "${palette[15]}" \
  --arg surface "${palette[8]}" \
  --arg surface_bright "${palette[8]}" \
  --arg red "${palette[1]}" --arg light_red "${palette[9]}" \
  --arg green "${palette[2]}" --arg light_green "${palette[10]}" \
  --arg yellow "${palette[3]}" --arg light_yellow "${palette[11]}" \
  --arg blue "${palette[4]}" --arg light_blue "${palette[12]}" \
  --arg magenta "${palette[5]}" --arg light_magenta "${palette[13]}" \
  --arg cyan "${palette[6]}" --arg light_cyan "${palette[14]}" \
  '{
    background: $surface,
    overBackground: $foreground,
    shadow: "#000000",
    scrim: "#000000",
    surface: $surface,
    surfaceDim: $background,
    surfaceBright: $surface_bright,
    surfaceContainer: $surface,
    surfaceContainerHigh: $surface_bright,
    surfaceContainerHighest: $surface_bright,
    surfaceContainerLow: $surface,
    surfaceContainerLowest: $background,
    surfaceVariant: $surface_bright,
    surfaceTint: $blue,
    overSurface: $foreground,
    overSurfaceVariant: $foreground,
    outline: $foreground,
    outlineVariant: $surface_bright,
    primary: $blue,
    primaryContainer: $surface_bright,
    primaryFixed: $light_blue,
    primaryFixedDim: $blue,
    overPrimary: $background,
    overPrimaryContainer: $foreground,
    overPrimaryFixed: $background,
    overPrimaryFixedVariant: $background,
    secondary: $magenta,
    secondaryContainer: $surface_bright,
    secondaryFixed: $light_magenta,
    secondaryFixedDim: $magenta,
    overSecondary: $background,
    overSecondaryContainer: $foreground,
    overSecondaryFixed: $background,
    overSecondaryFixedVariant: $background,
    tertiary: $cyan,
    tertiaryContainer: $surface_bright,
    tertiaryFixed: $light_cyan,
    tertiaryFixedDim: $cyan,
    overTertiary: $background,
    overTertiaryContainer: $foreground,
    overTertiaryFixed: $background,
    overTertiaryFixedVariant: $background,
    inverseSurface: $foreground,
    inverseOnSurface: $background,
    inversePrimary: $light_blue,
    red: $red, lightRed: $light_red, redContainer: $surface_bright, redSource: $red, redValue: $red,
    overRed: $background, overRedContainer: $foreground,
    green: $green, lightGreen: $light_green, greenContainer: $surface_bright, greenSource: $green, greenValue: $green,
    overGreen: $background, overGreenContainer: $foreground,
    yellow: $yellow, lightYellow: $light_yellow, yellowContainer: $surface_bright, yellowSource: $yellow, yellowValue: $yellow,
    overYellow: $background, overYellowContainer: $foreground,
    blue: $blue, lightBlue: $light_blue, blueContainer: $surface_bright, blueSource: $blue, blueValue: $blue,
    overBlue: $background, overBlueContainer: $foreground,
    magenta: $magenta, lightMagenta: $light_magenta, magentaContainer: $surface_bright, magentaSource: $magenta, magentaValue: $magenta,
    overMagenta: $background, overMagentaContainer: $foreground,
    cyan: $cyan, lightCyan: $light_cyan, cyanContainer: $surface_bright, cyanSource: $cyan, cyanValue: $cyan,
    overCyan: $background, overCyanContainer: $foreground,
    white: $foreground, whiteContainer: $surface_bright, whiteSource: $foreground, whiteValue: $foreground,
    overWhite: $background, overWhiteContainer: $foreground,
    error: $light_red, errorContainer: $red, overError: $background, overErrorContainer: $foreground,
    sourceColor: $blue
  }' > "$temporary_path"

mv "$temporary_path" "$output_path"
trap - EXIT
echo "Generated rebos_shell colors with Wallust fallback."

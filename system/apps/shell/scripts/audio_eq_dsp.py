"""Portable ten-band PipeWire graph and conservative gain compensation."""
import cmath
import math
from functools import lru_cache

FREQUENCIES = (31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
SINK = 'enclosure.equalizer'
OUTPUT = 'enclosure.equalizer.output'
PRESETS = {
    'Flat': [0] * 10,
    'Music': [2, 2, 1, 0, -1, 0, 1, 2, 1, 0],
    'Pop': [2, 2, 1, 0, -1, 0, 1, 2, 2, 1],
    'Rock': [2, 2, 1, -1, -1, 1, 2, 3, 2, 1],
    'Hip-Hop': [4, 4, 3, 1, -1, 0, 1, 1, 1, 0],
    'Electronic': [4, 3, 2, 0, -1, 0, 1, 2, 3, 2],
    'Jazz': [1, 1, 0, 0, 1, 1, 2, 1, 1, 0],
    'Classical': [0, 0, 0, 0, 0, 1, 1, 1, 2, 1],
    'Acoustic': [-1, 0, 1, 1, 1, 2, 2, 1, 0, 0],
    'Lo-fi': [2, 2, 1, 0, 0, -1, -1, -2, -3, -4],
    'YouTube': [-2, -1, 0, 0, 1, 2, 2, 1, 0, -1],
    'Podcasts': [-4, -3, -1, 0, 1, 3, 3, 1, -1, -2],
    'Speech': [-5, -4, -2, 0, 1, 3, 3, 2, 0, -2],
    'Movies': [3, 2, 1, -1, 0, 2, 2, 1, 0, -1],
    'Gaming': [-2, -2, -1, 0, 1, 2, 3, 3, 1, -1],
    'Bass': [5, 4, 3, 1, 0, 0, 0, 0, 0, 0],
    'Treble': [0, 0, 0, 0, 0, 0, 1, 3, 4, 3],
}


def validate_gains(values):
    if not isinstance(values, list) or len(values) != 10:
        raise ValueError('Choose ten band values')
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not -12 <= value <= 12 for value in values):
        raise ValueError('Band values must be between -12 and +12 dB')
    return [round(value, 1) for value in values]


def coefficients(frequency, gain, rate=48000):
    amplitude = 10 ** (gain / 40)
    omega = 2 * math.pi * frequency / rate
    alpha = math.sin(omega) / (2 * 1.4)
    cosine = math.cos(omega)
    return ((1 + alpha * amplitude, -2 * cosine, 1 - alpha * amplitude),
            (1 + alpha / amplitude, -2 * cosine, 1 - alpha / amplitude))


def response_db(gains, frequency):
    z = cmath.exp(-2j * math.pi * frequency / 48000)
    response = 1.0
    for center, gain in zip(FREQUENCIES, gains):
        numerator, denominator = coefficients(center, gain)
        response *= abs(sum(value * z ** i for i, value in enumerate(numerator)) /
                        sum(value * z ** i for i, value in enumerate(denominator)))
    return 20 * math.log10(max(response, 1e-12))


def headroom(gains):
    return _headroom(tuple(gains))


@lru_cache(maxsize=128)
def _headroom(gains):
    if not any(gain > 0 for gain in gains):
        return 0.0
    # Sweep the complete cascade, including each center frequency. Leave 1 dB
    # beyond its highest steady-state response; do not amplify cut-only curves.
    frequencies = list(FREQUENCIES) + [20 * (23900 / 20) ** (i / 511) for i in range(512)]
    peak = max(response_db(gains, frequency) for frequency in frequencies)
    return -round(max(0, peak + 1), 2)


def controls(gains):
    values = {'preamp:Mult': 10 ** (headroom(gains) / 20)}
    values.update({f'band{i}:Gain': value for i, value in enumerate(gains)})
    return values


def graph(gains, target):
    settings = controls(gains)
    nodes = [{'type': 'builtin', 'name': 'preamp', 'label': 'linear',
              'control': {'Mult': settings['preamp:Mult'], 'Add': 0}}]
    nodes.extend({'type': 'builtin', 'name': f'band{i}', 'label': 'bq_peaking',
                  'control': {'Freq': frequency, 'Q': 1.4, 'Gain': gains[i]}}
                 for i, frequency in enumerate(FREQUENCIES))
    names = ['preamp'] + [f'band{i}' for i in range(10)]
    links = [{'output': f'{left}:Out', 'input': f'{right}:In'}
             for left, right in zip(names, names[1:])]
    return {
        'context.properties': {'log.level': 0},
        'context.spa-libs': {'audio.convert.*': 'audioconvert/libspa-audioconvert',
                             'support.*': 'support/libspa-support'},
        'context.modules': [
            {'name': 'libpipewire-module-protocol-native'},
            {'name': 'libpipewire-module-client-node'},
            {'name': 'libpipewire-module-adapter'},
            {'name': 'libpipewire-module-filter-chain', 'args': {
                'node.description': 'Enclosure Equalizer',
                'filter.graph': {'nodes': nodes, 'links': links},
                'audio.channels': 2, 'audio.position': ['FL', 'FR'], 'audio.rate': 48000,
                'capture.props': {'node.name': SINK, 'media.class': 'Audio/Sink',
                                  'priority.session': 0, 'node.virtual': True},
                'playback.props': {'node.name': OUTPUT, 'node.passive': True,
                                   'target.object': target, 'node.dont-fallback': True},
            }},
        ],
    }

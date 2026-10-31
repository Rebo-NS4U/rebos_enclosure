"""Read real MP4 movie duration before allowing provider resources to play."""
import struct
from urllib.request import Request, urlopen


class InvalidMedia(RuntimeError):
    pass


def mp4_duration(read_at):
    """Walk ISO BMFF boxes via bounded reads; skip the large mdat payload."""
    offset = 0
    for _ in range(80):
        header = read_at(offset, 16)
        if len(header) < 8:
            break
        size, kind = struct.unpack('>I4s', header[:8])
        header_size = 8
        if size == 1:
            if len(header) < 16:
                break
            size = struct.unpack('>Q', header[8:16])[0]
            header_size = 16
        if size < header_size:
            break
        if kind == b'moov':
            if size > 8_000_000:
                raise InvalidMedia('The video metadata is unexpectedly large.')
            data = read_at(offset + header_size, size - header_size)
            cursor = 0
            while cursor + 8 <= len(data):
                length, child = struct.unpack('>I4s', data[cursor:cursor + 8])
                if length < 8 or cursor + length > len(data):
                    break
                if child == b'mvhd':
                    payload = data[cursor + 8:cursor + length]
                    if len(payload) < 20:
                        break
                    if payload[0] == 1:
                        if len(payload) < 32:
                            break
                        scale, duration = struct.unpack('>IQ', payload[20:32])
                    else:
                        scale, duration = struct.unpack('>II', payload[12:20])
                    if scale and duration:
                        return duration / scale
                cursor += length
            break
        offset += size
    raise InvalidMedia('Could not verify the actual video duration. Playback was blocked.')


def remote_duration(url):
    def read_at(offset, length):
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': f'bytes={offset}-{offset + length - 1}', 'Accept-Encoding': 'identity'})
        try:
            with urlopen(request, timeout=12) as response:
                if response.status != 206 and offset:
                    raise InvalidMedia('The source does not support verification of this video.')
                return response.read(length)
        except OSError:
            raise InvalidMedia('Could not verify the video source. Please retry later.') from None
    return mp4_duration(read_at)


def validate_duration(expected, actual):
    if actual <= 0 or (expected and expected >= 120 and actual < expected * .65):
        raise InvalidMedia('The movie/TV provider returned a short announcement or preview instead of the requested title. Playback was blocked.')
    return actual

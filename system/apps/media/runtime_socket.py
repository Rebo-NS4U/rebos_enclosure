"""Remove only a confirmed stale, owned Unix socket; preserve other paths."""
import errno
import os
import socket
import stat


def socket_identity(path):
    info = path.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError('Refusing to replace a non-socket or foreign-owned path: ' + str(path))
    return info.st_dev, info.st_ino


def unlink_socket(path, identity):
    try:
        current = socket_identity(path)
    except (FileNotFoundError, RuntimeError):
        return False
    if current != identity:
        return False
    path.unlink()
    return True


def prepare_socket(path):
    try:
        identity = socket_identity(path)
    except FileNotFoundError:
        return
    with socket.socket(socket.AF_UNIX) as probe:
        probe.settimeout(.5)
        try:
            probe.connect(str(path))
        except OSError as error:
            if error.errno == errno.ENOENT:
                return
            if error.errno != errno.ECONNREFUSED:
                raise RuntimeError('Cannot safely inspect the media socket: ' + str(path)) from error
        else:
            raise RuntimeError('Anime service is already running')
    if not unlink_socket(path, identity):
        raise RuntimeError('Media socket changed during startup; refusing to replace it')

"""Preload spotDL once; fork isolated, cancellable jobs on Linux."""
import json
import os
import sys
import traceback


def emit(**data):
    print(json.dumps(data), flush=True)


def main():
    # The controller uses spotDL's own interpreter when available. External
    # launchers remain supported through exec when their module isn't importable.
    try:
        if "--native" not in sys.argv:
            raise ImportError
        from spotdl.console.entry_point import console_entry_point
        from SpotipyFree import Spotify
        from track_cache import cached_track
        Spotify.track = cached_track(Spotify.track)
    except ImportError:
        console_entry_point = None
    for line in sys.stdin:
        command = json.loads(line)
        read_fd, write_fd = os.pipe()
        sys.stdout.flush()
        pid = os.fork()
        if pid == 0:
            code = 1
            try:
                os.setsid()
                os.close(read_fd)
                os.dup2(write_fd, 1)
                os.dup2(write_fd, 2)
                os.close(write_fd)
                with open(os.devnull) as source:
                    os.dup2(source.fileno(), 0)
                if console_entry_point is None:
                    os.execv(command[0], command)
                sys.argv = command
                console_entry_point()
                code = 0
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else (1 if error.code else 0)
            except BaseException:
                traceback.print_exc()
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(code)
        os.close(write_fd)
        emit(pid=pid)
        with os.fdopen(read_fd) as output:
            for output_line in output:
                emit(log=output_line.rstrip())
        _, status = os.waitpid(pid, 0)
        emit(done=True, code=os.waitstatus_to_exitcode(status))


if __name__ == '__main__':
    main()

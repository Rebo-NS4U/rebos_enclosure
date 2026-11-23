#!/usr/bin/env python3
"""Unprivileged process samples. Only concise identity labels are emitted; full command lines and environments are never emitted."""
import json
import signal
import os
from pathlib import Path
import subprocess
import sys
import time


def process_name(base, fallback):
    """Resolve untruncated executable names and a small set of useful identities."""
    try:
        name = Path(os.readlink(base / 'exe')).name.removesuffix(' (deleted)')
    except OSError:
        return fallback
    try:
        with (base / 'cmdline').open('rb') as stream:
            args = [arg.decode('utf-8', errors='replace') for arg in stream.read(8192).split(b'\0') if arg]
    except OSError:
        return name
    label = name
    if name.startswith(('python', 'node', 'ruby', 'perl')) or name in ('bash', 'sh', 'zsh', 'fish'):
        if len(args) > 2 and args[1] == '-m':
            label = args[2] + ' (' + name + ')'
        elif len(args) > 1 and not args[1].startswith('-'):
            label = Path(args[1]).name + ' (' + name + ')'
    roles = {'renderer': 'Renderer', 'gpu-process': 'GPU worker', 'utility': 'Utility worker',
             'zygote': 'Process launcher', 'crashpad-handler': 'Crash handler'}
    for arg in args[1:]:
        if arg.startswith('--type=') and arg[7:] in roles:
            label += ' · ' + roles[arg[7:]]
            break
    return ''.join(char for char in label if char.isprintable())[:160] or fallback


def process_swap(base):
    try:
        with (base / 'status').open() as stream:
            for line in stream:
                if line.startswith('VmSwap:'):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


class ProcessMonitor:
    def __init__(self, proc=Path('/proc')):
        self.proc = proc
        self.previous = {}
        self.timestamp = None
        self.ticks = os.sysconf('SC_CLK_TCK')
        self.page_size = os.sysconf('SC_PAGE_SIZE')

    # Quality exception: Independent hardware/process counters have different units and are kept explicitly named.
    # Numeric ceilings are enforced by desktop/scripts/quality.py.
    def snapshot(self, pid, summary=False):  # pylint: disable=too-many-locals
        base = self.proc / str(pid)
        stat = (base / 'stat').read_text()
        end = stat.rfind(')')
        fields = stat[end + 2:].split()
        row = dict(pid=int(pid), ppid=int(fields[1]), name=stat[stat.find('(') + 1:end],
                   start=int(fields[19]), ticks=int(fields[11]) + int(fields[12]),
                   ram=max(0, int(fields[21])) * self.page_size,
                   read=0, write=0, io_available=False, sockets=0, gpu={})
        row['name'] = process_name(base, row['name'])
        try:
            values = dict(line.split(':', 1) for line in (base / 'io').read_text().splitlines())
            row.update(read=int(values['read_bytes']), write=int(values['write_bytes']), io_available=True)
        except (OSError, ValueError, KeyError):
            pass
        if summary:
            return row
        clients = set()
        try:
            for fd in (base / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    if target.startswith('socket:'):
                        row['sockets'] += 1
                    if not target.startswith('/dev/dri/'):
                        continue
                    info = (base / 'fdinfo' / fd.name).read_text()
                    values = dict(line.split(':', 1) for line in info.splitlines() if ':' in line)
                    device = values.get('drm-pdev', '').strip()
                    client = (device, values.get('drm-client-id', fd.name).strip())
                    if not device or client in clients:
                        continue
                    clients.add(client)
                    counters = [int(v.strip().split()[0]) for k, v in values.items()
                                if k.startswith('drm-engine-') and v.strip().endswith(' ns')]
                    if not counters:
                        continue
                    engines = sum(counters)
                    row['gpu'][device] = row['gpu'].get(device, 0) + engines
                except (OSError, ValueError):
                    continue
        except OSError:
            pass
        return row

    def sample(self, memory_accounting=False, summary=False):
        now = time.monotonic()
        elapsed = now - self.timestamp if self.timestamp is not None else None
        current = {}
        rows = []
        for base in self.proc.iterdir():
            if not base.name.isdigit():
                continue
            try:
                row = self.snapshot(base.name, summary=summary)
            except (OSError, ValueError, IndexError):
                continue
            if memory_accounting:
                row['ram'], row['memory_available'] = self.proportional_memory(base)
            current[row['pid']] = row
            old = self.previous.get(row['pid'])
            valid = elapsed and old and old['start'] == row['start']
            result = {key: row[key] for key in ('pid', 'ppid', 'start', 'name', 'ram', 'sockets', 'io_available')}
            if summary:
                result['swap'] = process_swap(base)
            if memory_accounting:
                result['memory_available'] = row['memory_available']
            result['cpu'] = max(0, (row['ticks'] - old['ticks']) / self.ticks / elapsed * 100) if valid else 0
            if valid and old['io_available'] and row['io_available']:
                result['disk'] = max(0, row['read'] - old['read'] + row['write'] - old['write']) / elapsed
            else:
                result['disk'] = None if summary else 0
            result['gpu'] = {dev: max(0, ns - old['gpu'].get(dev, ns)) / (elapsed * 1e9) * 100 if valid else 0
                             for dev, ns in row['gpu'].items()}
            rows.append(result)
        self.previous, self.timestamp = current, now
        if memory_accounting:
            values = dict(line.split(':', 1) for line in (self.proc / 'meminfo').read_text().splitlines())
            total = int(values['MemTotal'].split()[0]) * 1024
            available = int(values['MemAvailable'].split()[0]) * 1024
            attributed = sum(row['ram'] for row in rows)
            return dict(processes=rows, memory=dict(total=total, available=available,
                        used=total - available, attributed=attributed,
                        other=total - available - attributed,
                        unreadable=sum(not row['memory_available'] for row in rows)))
        return rows

    @staticmethod
    def proportional_memory(base):
        """Count shared pages proportionally; never silently substitute duplicated RSS."""
        try:
            with (base / 'smaps_rollup').open() as stream:
                for line in stream:
                    if line.startswith('Pss:'):
                        return int(line.split()[1]) * 1024, True
        except (OSError, ValueError):
            pass
        return 0, False


def pick_window():
    try:
        picked = subprocess.run(['niri', 'msg', '-j', 'pick-window'], capture_output=True, text=True, timeout=120)
        if picked.returncode:
            return {'error': 'Window selection cancelled or unavailable.'}
        window = json.loads(picked.stdout)
        if not window:
            return {'error': 'Window selection cancelled.'}
        result = {'window': window}
        pid = window.get('pid')
        if pid:
            try:
                monitor = ProcessMonitor()
                row = monitor.snapshot(pid)
                result['process'] = {key: row[key] for key in ('pid', 'ppid', 'name', 'ram', 'start')}
                result['process']['exe'] = os.readlink(f'/proc/{pid}/exe')
            except (OSError, ValueError, IndexError):
                result['process_note'] = 'Process exited or its details are unavailable.'
        return result
    except subprocess.TimeoutExpired:
        return {'error': 'Window selection timed out.'}
    except (OSError, ValueError, TypeError):
        return {'error': 'Could not read window information.'}


def send_process_signal(pid, start, sig):
    if pid <= 1:
        raise ValueError("Invalid process")
    fd = os.pidfd_open(pid)
    try:
        if ProcessMonitor().snapshot(pid, summary=True)['start'] != start:
            raise ProcessLookupError("Process identity changed")
        signal.pidfd_send_signal(fd, sig)
    finally:
        os.close(fd)


# Quality exception: Independent rejection guard clauses keep invalid captions and stale process actions fail-closed.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
def window_action(action, window_id, pid, start):  # pylint: disable=too-many-return-statements
    """Act only on the selected window and the same process incarnation."""
    if action not in ('close', 'terminate', 'kill'):
        return {'error': 'Unknown window action.'}
    try:
        window_id, pid = int(window_id), int(pid)
        listed = subprocess.run(['niri', 'msg', '-j', 'windows'], capture_output=True, text=True, timeout=5, check=True)
        window = next((w for w in json.loads(listed.stdout) if w['id'] == window_id), None)
        if window is None or (window.get('pid') or 0) != pid:
            return {'error': 'That window has closed or changed. Pick a window again.'}
        if action == 'close':
            subprocess.run(['niri', 'msg', 'action', 'close-window', '--id', str(window_id)],
                           capture_output=True, text=True, timeout=5, check=True)
            return {'message': 'Close requested.'}
        if pid <= 1 or not start:
            return {'error': 'Process information is unavailable. Pick the window again.'}
        send_process_signal(pid, int(start), signal.SIGTERM if action == 'terminate' else signal.SIGKILL)
        return {'message': 'Termination requested.' if action == 'terminate' else 'Force kill sent.',
                'killed': action == 'kill'}
    except ProcessLookupError:
        return {'error': 'The process has already exited.'}
    except PermissionError:
        return {'error': 'You do not have permission to control this process.'}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {'error': 'Could not control this window. Pick it again and retry.'}


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == '--window-action':
        print(json.dumps(window_action(*sys.argv[2:])), flush=True)
    elif len(sys.argv) == 4 and sys.argv[1] == '--terminate':
        try:
            send_process_signal(int(sys.argv[2]), int(sys.argv[3]), signal.SIGTERM)
        except (ValueError, OSError) as error:
            sys.exit(str(error))
    elif '--pick-window' in sys.argv:
        print(json.dumps(pick_window()), flush=True)
    else:
        monitor = ProcessMonitor()
        try:
            while True:
                sample = monitor.sample(memory_accounting='--memory-accounting' in sys.argv, summary='--summary' in sys.argv)
                print(json.dumps(sample), flush=True)
                time.sleep(1)
        except (BrokenPipeError, KeyboardInterrupt):
            pass

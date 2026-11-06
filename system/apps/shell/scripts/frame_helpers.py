"""Consistent bounded frame rendering for wallpaper cache commands."""
import subprocess


def render_frame(command, output_path, *, timeout=30):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and output_path.exists():
            return True, 'Success'
        return False, result.stderr.strip() if result.stderr else 'Unknown error'
    except subprocess.TimeoutExpired:
        return False, 'Timeout'
    except Exception as error:
        return False, str(error)

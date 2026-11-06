"""Immutable episode identity captured across asynchronous player callbacks."""
from typing import NamedTuple


class PlaybackContext(NamedTuple):
    show: dict
    episodes: list
    index: int
    token: int

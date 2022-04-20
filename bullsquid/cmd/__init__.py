"""Provides __version__ for us in CLI --version output."""
from importlib.metadata import version

__version__ = version("bullsquid")

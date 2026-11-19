"""Console entry for Livegrab.

Importing this module does not bind a port or start a download.
"""

from livegrab_lib.server import main as serve


def main():
    """Start the same server as ``python livegrab.py``."""
    return serve()

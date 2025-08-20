"""CLI package."""

from cli.chat_cli import main as chat_main
from cli.manage import main as manage_main

__all__ = ["chat_main", "manage_main"]
"""CLI package initialization."""

from .chat import app as chat_app
from .manage import app as manage_app

__all__ = ["chat_app", "manage_app"]
"""Shared desktop styles – re-export theme stylesheets."""

from desktop.theme import DARK_STYLESHEET, LIGHT_STYLESHEET, stylesheet_for

# Back-compat for older imports
APP_STYLESHEET = LIGHT_STYLESHEET

__all__ = ["APP_STYLESHEET", "LIGHT_STYLESHEET", "DARK_STYLESHEET", "stylesheet_for"]

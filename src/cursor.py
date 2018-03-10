"""cursor.py - Cursor handler."""

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

NORMAL, GRAB, WAIT = range(3)


class CursorHandler:

    def __init__(self, window):
        self._window = window
        self._timer_id = None
        self._auto_hide = False
        self._current_cursor = NORMAL

    def set_cursor_type(self, cursor):
        """Set the cursor to type <cursor>. Supported cursor types are
        available as constants in this module. If <cursor> is not one of the
        cursor constants above, it must be a Gdk.Cursor.
        """
        if cursor == NORMAL:
            mode = None
        elif cursor == GRAB:
            mode = Gdk.Cursor.new(Gdk.CursorType.FLEUR)
        elif cursor == WAIT:
            mode = Gdk.Cursor.new(Gdk.CursorType.WATCH)
        else:
            mode = cursor
        self._window.set_cursor(mode)
        self._current_cursor = cursor
        if self._auto_hide:
            if cursor == NORMAL:
                self._set_hide_timer()
            else:
                self._kill_timer()

    def auto_hide_on(self):
        """Signal that the cursor should auto-hide from now on (e.g. that
        we are entering fullscreen).
        """
        self._auto_hide = True
        if self._current_cursor == NORMAL:
            self._set_hide_timer()

    def auto_hide_off(self):
        """Signal that the cursor should *not* auto-hide from now on."""
        self._auto_hide = False
        self._kill_timer()
        if self._current_cursor == NORMAL:
            self.set_cursor_type(NORMAL)

    def refresh(self):
        """Refresh the current cursor (i.e. display it and set a new timer in
        fullscreen). Used when we move the cursor.
        """
        if self._auto_hide:
            self.set_cursor_type(self._current_cursor)

    def _set_hide_timer(self):
        self._kill_timer()
        self._timer_id = GObject.timeout_add(2000, self._window.set_cursor,
            self._get_hidden_cursor())

    def _kill_timer(self):
        if self._timer_id is not None:
            GObject.source_remove(self._timer_id)
            self._timer_id = None

    def _get_hidden_cursor(self):
        return Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)

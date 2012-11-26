"""labels.py - Gtk.Label convenience classes."""

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GLib

'''
The required Pango Attributes are not introspectable so we're messing around
with Pango markup instead.
'''

class FormattedLabel(Gtk.Label):
    
    """FormattedLabel keeps a label always formatted with some pango weight,
    style and scale, even when new text is set using set_text().
    """
    
    def __init__(self, text='', weight=Pango.Weight.NORMAL,
                 style=Pango.Style.NORMAL, size=None):
        self._format = "<span"

        Gtk.Label.__init__(self)

        if weight == Pango.Weight.BOLD:
            self._format += " weight='bold'"
        elif weight == Pango.Weight.HEAVY:
            self._format += " weight='heavy'"
        elif weight == Pango.Weight.ULTRABOLD:
            self._format += " weight='ultrabold'"

        if style == Pango.Style.ITALIC:
            self._format += " style='italic'"
        elif style == Pango.Style.OBLIQUE:
            self._format += " style='oblique'"

        if size:
            self._format += " size='%s'" % size

        self._format += ">%s</span>"
        self.set_markup(self._format % GLib.markup_escape_text(text))

    def set_text(self, text):
        self.set_markup(self._format % GLib.markup_escape_text(text))

class BoldLabel(FormattedLabel):
    
    """A FormattedLabel that is always bold and otherwise normal."""
    
    def __init__(self, text=''):
        Gtk.Label.__init__(self)
        self._format = "<b>%s</b>"
        self.set_markup(self._format % GLib.markup_escape_text(text))

class ItalicLabel(FormattedLabel):
    
    """A FormattedLabel that is always italic and otherwise normal."""
    
    def __init__(self, text=''):
        Gtk.Label.__init__(self)
        self._format = "<i>%s</i>"
        self.set_markup(self._format % GLib.markup_escape_text(text))

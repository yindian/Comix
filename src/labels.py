"""labels.py - Gtk.Label convenience classes."""

from gi.repository import Gtk
from gi.repository import Pango


class FormattedLabel(Gtk.Label):
    
    """FormattedLabel keeps a label always formatted with some pango weight,
    style and scale, even when new text is set using set_text().
    """
    
    def __init__(self, text='', weight=Pango.Weight.NORMAL,
      style=Pango.Style.NORMAL, scale=Pango.SCALE_MEDIUM):
        GObject.GObject.__init__(self, text)
        self._weight = weight
        self._style = style
        self._scale = scale
        self._format()

    def set_text(self, text):
        Gtk.Label.set_text(self, text)
        self._format()

    def _format(self):
        text_len = len(self.get_text())
        attrlist = Pango.AttrList()
        attrlist.insert(Pango.AttrWeight(self._weight, 0, text_len))
        attrlist.insert(Pango.AttrStyle(self._style, 0, text_len))
        attrlist.insert(Pango.AttrScale(self._scale, 0, text_len))
        self.set_attributes(attrlist)


class BoldLabel(FormattedLabel):
    
    """A FormattedLabel that is always bold and otherwise normal."""
    
    def __init__(self, text=''):
        FormattedLabel.__init__(self, text, weight=Pango.Weight.BOLD)


class ItalicLabel(FormattedLabel):
    
    """A FormattedLabel that is always italic and otherwise normal."""
    
    def __init__(self, text=''):
        FormattedLabel.__init__(self, text, style=Pango.Style.ITALIC)

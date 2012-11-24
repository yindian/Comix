"""comment.py - Comments dialog."""

import os

from gi.repository import Gtk
from gi.repository import Pango

import encoding

_dialog = None


class _CommentsDialog(Gtk.Dialog):

    def __init__(self, window):
        GObject.GObject.__init__(self, _('Comments'), window, 0,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_has_separator(False)
        self.set_resizable(True)
        self.connect('response', _close_dialog)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        self.set_default_size(600, 550)

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        self.set_border_width(4)
        notebook.set_border_width(6)
        self.vbox.pack_start(notebook, True, True, 0)
        tag = Gtk.TextTag()
        tag.set_property('editable', False)
        tag.set_property('editable-set', True)
        tag.set_property('family', 'Monospace')
        tag.set_property('family-set', True)
        tag.set_property('scale', 0.9)
        tag.set_property('scale-set', True)
        tag_table = Gtk.TextTagTable()
        tag_table.add(tag)

        for num in xrange(1, window.file_handler.get_number_of_comments() + 1):
            page = Gtk.VBox(False)
            page.set_border_width(8)
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            page.pack_start(scrolled, True, True, 0)
            outbox = Gtk.EventBox()
            scrolled.add_with_viewport(outbox)
            inbox = Gtk.EventBox()
            inbox.set_border_width(6)
            outbox.add(inbox)
            name = os.path.basename(window.file_handler.get_comment_name(num))
            text = window.file_handler.get_comment_text(num)
            if text is None:
                text = _('Could not read %s') % path
            text_buffer = Gtk.TextBuffer(tag_table)
            text_buffer.set_text(encoding.to_unicode(text))
            text_buffer.apply_tag(tag, *text_buffer.get_bounds())
            text_view = Gtk.TextView(text_buffer)
            inbox.add(text_view)
            bg_color = text_view.get_default_attributes().bg_color
            outbox.modify_bg(Gtk.StateType.NORMAL, bg_color)
            tab_label = Gtk.Label(label=encoding.to_unicode(name))
            notebook.insert_page(page, tab_label)

        self.show_all()


def open_dialog(action, window):
    """Create and display the (singleton) comments dialog."""
    global _dialog
    if _dialog is None:
        _dialog = _CommentsDialog(window)
    else:
        _dialog.present()


def _close_dialog(*args):
    """Destroy the comments dialog."""
    global _dialog
    if _dialog is not None:
        _dialog.destroy()
        _dialog = None

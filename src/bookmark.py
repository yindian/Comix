"""bookmark.py - Bookmarks handler (including menu and dialog)."""

import os
import cPickle

from gi.repository import Gtk
from gi.repository import GObject

import constants
import constants

_pickle_path = os.path.join(constants.DATA_DIR, 'bookmarks.pickle')


class BookmarksMenu(Gtk.Menu):

    """BookmarksMenu extends Gtk.Menu with convenience methods relating to
    bookmarks. It contains fixed items for adding bookmarks etc. as well
    as dynamic items corresponding to the current bookmarks.
    """

    def __init__(self, ui, window):
        GObject.GObject.__init__(self)

        self._window = window
        self._actiongroup = Gtk.ActionGroup('comix-bookmarks')
        self._actiongroup.add_actions([
            ('add_bookmark', 'comix-add-bookmark', _('_Add bookmark'),
                '<Control>d', None, self._add_current_to_bookmarks),
            ('edit_bookmarks', None, _('_Edit bookmarks...'),
                '<Control>b', None, self._edit_bookmarks),
            ('clear_bookmarks', Gtk.STOCK_CLEAR, _('_Clear bookmarks...'),
                None, None, self._clear_bookmarks)])
        self._separator = Gtk.SeparatorMenuItem()

        action = self._actiongroup.get_action('add_bookmark')
        action.set_accel_group(ui.get_accel_group())
        self.append(action.create_menu_item())
        action = self._actiongroup.get_action('edit_bookmarks')
        action.set_accel_group(ui.get_accel_group())
        self.append(action.create_menu_item())
        self.append(self._separator)
        self.append(Gtk.SeparatorMenuItem())
        action = self._actiongroup.get_action('clear_bookmarks')
        action.set_accel_group(ui.get_accel_group())
        self.append(action.create_menu_item())

        self.show_all()
        self._separator.hide()
        self._bookmarks_store = _BookmarksStore(self, window.file_handler)

    def add_bookmark(self, bookmark):
        """Add <bookmark> to the menu."""
        self.insert(bookmark, 3)
        bookmark.show()
        self._separator.show()

    def remove_bookmark(self, bookmark):
        """Remove <bookmark> from the menu."""
        self.remove(bookmark)
        if self._bookmarks_store.is_empty():
            self._separator.hide()

    def _add_current_to_bookmarks(self, *args):
        """Add the currently viewed file to the bookmarks."""
        self._bookmarks_store.add_current_to_bookmarks()

    def _edit_bookmarks(self, *args):
        """Open the bookmarks dialog."""
        _BookmarksDialog(self._window, self._bookmarks_store)

    def _clear_bookmarks(self, *args):
        """Remove all bookmarks, if the user presses 'Yes' in a confirmation
        dialog.
        """
        choice_dialog = Gtk.MessageDialog(self._window, 0,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
            _('Clear all bookmarks?'))
        choice_dialog.format_secondary_text(
            _('All stored bookmarks will be removed. Are you sure that you want to continue?'))
        response = choice_dialog.run()
        choice_dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self._bookmarks_store.clear_bookmarks()

    def set_sensitive(self, loaded):
        """Set the sensitivities of menu items as appropriate if <loaded>
        represents whether a file is currently loaded in the main program
        or not.
        """
        self._actiongroup.get_action('add_bookmark').set_sensitive(loaded)

    def write_bookmarks_file(self):
        """Store relevant bookmark info in the comix directory."""
        self._bookmarks_store.write_bookmarks_file()


class _Bookmark(Gtk.ImageMenuItem):

    """_Bookmark represents one bookmark. It extends the Gtk.ImageMenuItem
    and is thus put directly in the bookmarks menu.
    """

    def __init__(self, file_handler, name, path, page, numpages, archive_type):
        self._name = name
        self._path = path
        self._page = page
        self._numpages = numpages
        self._archive_type = archive_type
        self._file_handler = file_handler

        GObject.GObject.__init__(self, str(self), False)
        if self._archive_type is not None:
            im = Gtk.Image.new_from_stock('comix-archive', Gtk.IconSize.MENU)
        else:
            im = Gtk.Image.new_from_stock('comix-image', Gtk.IconSize.MENU)
        self.set_image(im)
        self.connect('activate', self._load)

    def __str__(self):
        return '%s, (%d / %d)' % (self._name, self._page, self._numpages)

    def _load(self, *args):
        """Open the file and page the bookmark represents."""
        self._file_handler.open_file(self._path, self._page)

    def same_path(self, path):
        """Return True if the bookmark is for the file <path>."""
        return path == self._path

    def to_row(self):
        """Return a tuple corresponding to one row in the _BookmarkDialog's
        ListStore.
        """
        stock = self.get_image().get_stock()
        pixbuf = self.render_icon(*stock)
        page = '%d / %d' % (self._page, self._numpages)
        return (pixbuf, self._name, page, self)

    def pack(self):
        """Return a tuple suitable for pickling. The bookmark can be fully
        re-created using the values in the tuple.
        """
        return (self._name, self._path, self._page, self._numpages,
            self._archive_type)


class _BookmarksStore:

    """The _BookmarksStore is a backend for both the bookmarks menu and dialog.
    Changes in the _BookmarksStore is mirrored in both.
    """

    def __init__(self, menu, file_handler):
        self._menu = menu
        self._file_handler = file_handler
        self._bookmarks = []
        if os.path.isfile(_pickle_path):
            try:
                fd = open(_pickle_path, 'rb')
                version = cPickle.load(fd)
                packs = cPickle.load(fd)
                for pack in packs:
                    self.add_bookmark_by_values(*pack)
                fd.close()
            except Exception:
                print '! bookmark.py: Could not parse', _pickle_path
                print '! bookmark.py: Deleting corrupt bookmarks file.\n'
                os.remove(_pickle_path)
                self.clear_bookmarks()

    def add_bookmark_by_values(self, name, path, page, numpages, archive_type):
        """Create a bookmark and add it to the store and the menu."""
        bookmark = _Bookmark(self._file_handler, name, path, page, numpages,
            archive_type)
        self.add_bookmark(bookmark)

    def add_bookmark(self, bookmark):
        """Add the <bookmark> to the store and the menu."""
        self._bookmarks.append(bookmark)
        self._menu.add_bookmark(bookmark)

    def remove_bookmark(self, bookmark):
        """Remove the <bookmark> from the store and the menu."""
        self._bookmarks.remove(bookmark)
        self._menu.remove_bookmark(bookmark)

    def add_current_to_bookmarks(self):
        """Add the currently viewed file to the store and the menu."""
        name = self._file_handler.get_pretty_current_filename()
        path = self._file_handler.get_real_path()
        page = self._file_handler.get_current_page()
        numpages = self._file_handler.get_number_of_pages()
        archive_type = self._file_handler.archive_type
        for bookmark in self._bookmarks:
            if bookmark.same_path(path):
                self.remove_bookmark(bookmark)
                break
        return self.add_bookmark_by_values(name, path, page, numpages,
            archive_type)

    def clear_bookmarks(self):
        """Remove all bookmarks from the store and the menu."""
        for bookmark in self._bookmarks[:]:
            self.remove_bookmark(bookmark)

    def get_bookmarks(self):
        """Return all the bookmarks in the store."""
        return self._bookmarks

    def is_empty(self):
        """Return True if the store is currently empty."""
        return len(self._bookmarks) == 0

    def write_bookmarks_file(self):
        """Store relevant bookmark info in the comix directory."""
        fd = open(_pickle_path, 'wb')
        cPickle.dump(constants.VERSION, fd, cPickle.HIGHEST_PROTOCOL)
        packs = [bookmark.pack() for bookmark in self._bookmarks]
        cPickle.dump(packs, fd, cPickle.HIGHEST_PROTOCOL)
        fd.close()


class _BookmarksDialog(Gtk.Dialog):

    """_BookmarksDialog lets the user remove and/or rearrange bookmarks."""

    def __init__(self, window, bookmarks_store):
        GObject.GObject.__init__(self, _('Edit bookmarks'), window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_REMOVE, Gtk.ResponseType.NO, Gtk.STOCK_CLOSE,
            Gtk.ResponseType.CLOSE))
        self._bookmarks_store = bookmarks_store

        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(Gtk.ResponseType.CLOSE)

        scrolled = Gtk.ScrolledWindow()
        self.set_border_width(4)
        scrolled.set_border_width(6)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.vbox.pack_start(scrolled, True, True, 0)

        self._liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, GObject.TYPE_STRING,
            GObject.TYPE_STRING, _Bookmark)
        self._treeview = Gtk.TreeView(self._liststore)
        self._treeview.set_rules_hint(True)
        self._treeview.set_reorderable(True)
        self._selection = self._treeview.get_selection()
        scrolled.add(self._treeview)
        cellrenderer_text = Gtk.CellRendererText()
        cellrenderer_pbuf = Gtk.CellRendererPixbuf()
        self._icon_col = Gtk.TreeViewColumn(None, cellrenderer_pbuf)
        self._name_col = Gtk.TreeViewColumn(_('Name'), cellrenderer_text)
        self._page_col = Gtk.TreeViewColumn(_('Page'), cellrenderer_text)
        self._treeview.append_column(self._icon_col)
        self._treeview.append_column(self._name_col)
        self._treeview.append_column(self._page_col)
        self._icon_col.set_attributes(cellrenderer_pbuf, pixbuf=0)
        self._name_col.set_attributes(cellrenderer_text, text=1)
        self._page_col.set_attributes(cellrenderer_text, text=2)
        self._name_col.set_expand(True)
        self._icon_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._name_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._page_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.resize(450, 450)

        self.connect('response', self._response)
        self.connect('delete_event', self._close)
        self._treeview.connect('key_press_event', self._key_press_event)

        for bookmark in self._bookmarks_store.get_bookmarks():
            self._add_bookmark(bookmark)
        self.show_all()

    def _add_bookmark(self, bookmark):
        """Add the <bookmark> to the dialog."""
        self._liststore.prepend(bookmark.to_row())

    def _remove_selected(self):
        """Remove the currently selected bookmark from the dialog and from
        the store."""
        treeiter = self._selection.get_selected()[1]
        if treeiter is not None:
            bookmark = self._liststore.get_value(treeiter, 3)
            self._liststore.remove(treeiter)
            self._bookmarks_store.remove_bookmark(bookmark)

    def _response(self, dialog, response):
        if response == Gtk.ResponseType.CLOSE:
            self._close()
        elif response == Gtk.ResponseType.NO:
            self._remove_selected()

    def _key_press_event(self, dialog, event, *args):
        if event.keyval == Gdk.KEY_Delete:
            self._remove_selected()

    def _close(self, *args):
        """Close the dialog and update the _BookmarksStore with the new
        ordering."""
        ordering = []
        treeiter = self._liststore.get_iter_root()
        while treeiter is not None:
            bookmark = self._liststore.get_value(treeiter, 3)
            ordering.insert(0, bookmark)
            treeiter = self._liststore.iter_next(treeiter)
        for bookmark in ordering:
            self._bookmarks_store.remove_bookmark(bookmark)
            self._bookmarks_store.add_bookmark(bookmark)
        self.destroy()

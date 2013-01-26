"""recent.py - Recent files handler."""

import urllib

from gi.repository import Gtk

import preferences


class RecentFilesMenu(Gtk.RecentChooserMenu):

    def __init__(self, ui, window):
        self._window = window
        Gtk.RecentChooserMenu.__init__(self)
        self._manager = Gtk.RecentManager.get_default()

        self.set_sort_type(Gtk.RecentSortType.MRU)
        self.set_show_tips(True)

        rfilter = Gtk.RecentFilter()
        rfilter.add_application('Comix')
        self.add_filter(rfilter)

        self.connect('item_activated', self._load)

    def _load(self, *args):
        uri = self.get_current_uri()
        path = urllib.url2pathname(uri[7:])
        self._window.file_handler.open_file(path)

    def add(self, path):
        if not preferences.prefs['store recent file info']:
            return

        uri = 'file://' + urllib.pathname2url(path)
        self._manager.add_item(uri)

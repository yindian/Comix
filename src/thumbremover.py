"""thumbremover.py - Thumbnail maintenance module for Comix.
Removes and cleans up outdated and orphaned thumbnails.
"""

import os
import urllib

from gi.repository import Gtk
from gi.repository import Pango
import Image

import encoding
import labels
import constants

_dialog = None
_thumb_base = os.path.join(constants.HOME_DIR, '.thumbnails')


class _ThumbnailMaintenanceDialog(Gtk.Dialog):

    def __init__(self, window):
        self._num_thumbs = 0
        GObject.GObject.__init__(self, _('Thumbnail maintenance'), window, 0,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        button = self.add_button(_('Cleanup'), Gtk.ResponseType.OK)
        button.set_image(Gtk.Image.new_from_stock(
            Gtk.STOCK_CLEAR, Gtk.IconSize.BUTTON))
        self.set_has_separator(False)
        self.set_resizable(False)
        self.set_border_width(4)
        self.connect('response', self._response)
        self.set_default_response(Gtk.ResponseType.OK)
        main_box = Gtk.VBox(False, 5)
        main_box.set_border_width(6)
        self.vbox.pack_start(main_box, False, False)

        label = labels.BoldLabel(_('Cleanup thumbnails'))
        label.set_alignment(0, 0.5)
        attrlist = label.get_attributes()
        attrlist.insert(Pango.AttrScale(Pango.SCALE_LARGE, 0,
            len(label.get_text())))
        label.set_attributes(attrlist)
        main_box.pack_start(label, False, False, 2)
        main_box.pack_start(Gtk.HSeparator(, True, True, 0), False, False, 5)

        label = labels.ItalicLabel(
            _('Thumbnails for files (such as image files and comic book archives) are stored in your home directory. Many different applications use and create these thumbnails, but sometimes thumbnails remain even though the original files have been removed - wasting space. This dialog can cleanup your stored thumbnails by removing orphaned and outdated thumbnails.'))
        label.set_alignment(0, 0.5)
        label.set_line_wrap(True)
        main_box.pack_start(label, False, False, 10)

        hbox = Gtk.HBox(False, 10)
        main_box.pack_start(hbox, False, False)
        left_box = Gtk.VBox(True, 5)
        right_box = Gtk.VBox(True, 5)
        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)

        label = labels.BoldLabel('%s:' % _('Thumbnail directory'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        label = Gtk.Label(label='%s' % encoding.to_unicode(_thumb_base))
        label.set_alignment(0, 1.0)
        right_box.pack_start(label, True, True)

        label = labels.BoldLabel('%s:' % _('Total number of thumbnails'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        self._num_thumbs_label = Gtk.Label(label=_('Calculating...'))
        self._num_thumbs_label.set_alignment(0, 1.0)
        right_box.pack_start(self._num_thumbs_label, True, True)

        label = labels.BoldLabel('%s:' % _('Total size of thumbnails'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        self._size_thumbs_label = Gtk.Label(label=_('Calculating...'))
        self._size_thumbs_label.set_alignment(0, 1.0)
        right_box.pack_start(self._size_thumbs_label, True, True)

        label = labels.ItalicLabel(
            _('Do you want to cleanup orphaned and outdated thumbnails now?'))
        label.set_alignment(0, 0.5)
        main_box.pack_start(label, False, False, 10)

        self.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration(False)
        self._update_num_and_size()

    def _update_num_and_size(self):
        self._num_thumbs = 0
        size_thumbs = 0
        for subdir in ('normal', 'large'):
            dir_path = os.path.join(_thumb_base, subdir)
            if os.path.isdir(dir_path):
                for entry in os.listdir(dir_path):
                    entry_path = os.path.join(dir_path, entry)
                    if os.path.isfile(entry_path):
                        self._num_thumbs += 1
                        size_thumbs += os.stat(entry_path).st_size
        self._num_thumbs_label.set_text('%d' % self._num_thumbs)
        self._size_thumbs_label.set_text('%.1f MiB' % (size_thumbs / 1048576.0))

    def _response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            _ThumbnailRemover(self, self._num_thumbs)
            self._update_num_and_size()
        else:
            _close_dialog()


class _ThumbnailRemover(Gtk.Dialog):

    def __init__(self, parent, total_thumbs):
        self._total_thumbs = total_thumbs
        self._destroy = False
        GObject.GObject.__init__(self, _('Removing thumbnails'), parent, 0,
            (Gtk.STOCK_STOP, Gtk.ResponseType.CLOSE))
        self.set_size_request(400, -1)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.set_border_width(4)
        self.connect('response', self._response)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        main_box = Gtk.VBox(False, 5)
        main_box.set_border_width(6)
        self.vbox.pack_start(main_box, False, False)

        hbox = Gtk.HBox(False, 10)
        main_box.pack_start(hbox, False, False, 5)
        left_box = Gtk.VBox(True, 5)
        right_box = Gtk.VBox(True, 5)
        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)

        label = labels.BoldLabel('%s:' % _('Number of removed thumbnails'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        number_label = Gtk.Label(label='0')
        number_label.set_alignment(0, 1.0)
        right_box.pack_start(number_label, True, True)

        label = labels.BoldLabel('%s:' % _('Total size of removed thumbnails'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        size_label = Gtk.Label(label='0.0 MiB')
        size_label.set_alignment(0, 1.0)
        right_box.pack_start(size_label, True, True)

        bar = Gtk.ProgressBar()
        main_box.pack_start(bar, False, False)

        removing_label = labels.ItalicLabel()
        removing_label.set_alignment(0, 0.5)
        removing_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        main_box.pack_start(removing_label, False, False)

        self.show_all()

        iteration = 0.0
        removed_thumbs = 0
        thumbs_size = 0
        for subdir in ('normal', 'large'):
            dir_path = os.path.join(_thumb_base, subdir)
            if not os.path.isdir(dir_path) or not os.access(dir_path, os.X_OK):
                continue
            for entry in os.listdir(dir_path):
                if self._destroy:
                    return
                iteration += 1
                entry_path = os.path.join(dir_path, entry)
                if not os.path.isfile(entry_path) or not os.access(entry_path,
                  os.W_OK | os.R_OK):
                    continue
                try:
                    im_info = Image.open(entry_path).info
                    thumb_mtime = int(im_info['Thumb::MTime'])
                    src_path = _uri_to_path(im_info['Thumb::URI'])
                    broken = False
                except Exception:
                    src_path = '?'
                    broken = True
                else:
                    try:
                        src_mtime = os.stat(src_path).st_mtime
                    except Exception:
                        src_mtime = None
                # Thumb is orphaned, outdated or invalid.
                if (broken or not os.path.isfile(src_path) or
                  src_mtime != thumb_mtime):
                    size = os.stat(entry_path).st_size
                    try:
                        os.remove(entry_path)
                    except Exception:
                        continue
                    removed_thumbs += 1
                    thumbs_size += size
                    number_label.set_text('%d' % removed_thumbs)
                    size_label.set_text('%.1f MiB' % (thumbs_size / 1048576.0))
                    if broken:
                        src_path = '?'
                    else:
                        src_path = encoding.to_unicode(src_path)
                    removing_label.set_text(_("Removed thumbnail for '%s'") %
                        src_path)
                if iteration % 50 == 0:
                    bar.set_fraction(min(1, iteration / self._total_thumbs))
                while Gtk.events_pending():
                    Gtk.main_iteration(False)

        self._response()

    def _response(self, *args):
        self._destroy = True
        self.destroy()


def _uri_to_path(uri):
    """Return the path corresponding to the URI <uri>, unless it is a
    non-local resource in which case we return the pathname with the type
    identifier intact.
    """
    if uri.startswith('file://'):
        return urllib.url2pathname(uri[7:])
    else:
        return urllib.url2pathname(uri)


def open_dialog(action, window):
    global _dialog
    if _dialog is None:
        _dialog = _ThumbnailMaintenanceDialog(window)
    else:
        _dialog.present()


def _close_dialog(*args):
    global _dialog
    if _dialog is not None:
        _dialog.destroy()
        _dialog = None

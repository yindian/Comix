"""archive.py - Archive handling (extract/create) for Comix."""

import sys
import os
import re
try:
    import czipfile as zipfile
except:
    import zipfile
import tarfile
import threading

from gi.repository import Gtk
from gi.repository import Gtk as gtk
gtk.MESSAGE_QUESTION = Gtk.MessageType.QUESTION
gtk.MESSAGE_WARNING = Gtk.MessageType.WARNING
gtk.BUTTONS_OK_CANCEL = Gtk.ButtonsType.OK_CANCEL
gtk.BUTTONS_CLOSE = Gtk.ButtonsType.CLOSE
gtk.RESPONSE_OK = Gtk.ResponseType.OK

import process
import time
import urllib
import traceback

ZIP, RAR, TAR, GZIP, BZIP2 = range(5)
P7ZIP = 5

_rar_exec = None
_7z_exec = None
_last_pass = ""

def win_hack(f):
    if type(f) == unicode:
        f = f.encode('mbcs', 'replace')
    try:
        f.encode('ascii')
    except:
        s, e = os.path.splitext(f)
        ar = s.split('\\')
        for i in xrange(len(ar)):
            try:
                ar[i].encode('ascii')
            except:
                ar[i] = ar[i].encode('base64').replace('\n', '').replace('+', '-').replace('/', '_')
        f = '\\'.join(ar) + e
    return f

def win_rename(dst, name):
    if not os.path.exists(os.path.join(dst, name)):
        return
    f = win_hack(name)
    if f != name:
        try:
            try:
                os.rename(os.path.join(dst, name), os.path.join(dst, f))
            except:
                os.makedirs(os.path.dirname(os.path.join(dst, f)))
                os.rename(os.path.join(dst, name), os.path.join(dst, f))
            #print "Renamed %s to %s under %s" % (name, f, dst)
        except:
            traceback.print_exc()
    else:
        #print "Kept %s under %s" % (name, dst)
        pass

def no_rename(dst, name):
    pass

if sys.platform == "win32":
    rename = win_rename
else:
    rename = no_rename

def hfs_hack(f):
    if sys.platform == 'darwin':
        if type(f) == unicode:
            f = f.encode('utf-8')
        else:
            try:
                f.decode('utf-8')
            except:
                try:
                    f = f.decode('cp936').encode('utf-8')
                except:
                    f = urllib.quote(f)
    return f

class Extractor:

    """Extractor is a threaded class for extracting different archive formats.

    The Extractor can be loaded with paths to archives (currently ZIP, tar,
    or RAR archives) and a path to a destination directory. Once an archive
    has been set it is possible to filter out the files to be extracted and
    set the order in which they should be extracted. The extraction can
    then be started in a new thread in which files are extracted one by one,
    and a signal is sent on a condition after each extraction, so that it is
    possible for other threads to wait on specific files to be ready.

    Note: Support for gzip/bzip2 compressed tar archives is limited, see
    set_files() for more info.
    """

    def __init__(self):
        self._setupped = False

    def setup(self, src, dst):
        """Setup the extractor with archive <src> and destination dir <dst>.
        Return a threading.Condition related to the is_ready() method, or
        None if the format of <src> isn't supported.
        """
        self._src = src
        self._dst = dst
        self._type = archive_mime_type(src)
        self._files = []
        self._extracted = {}
        self._stop = False
        self._extract_thread = None
        self._condition = threading.Condition()
        self._rarpass = '-p-'
	global _last_pass

        if self._type == ZIP:
            self._zfile = zipfile.ZipFile(src, 'r')
	    need_pass = False
	    for info in self._zfile.infolist():
		    if info.flag_bits & 0x1:
			    need_pass = True
			    break
            if need_pass:
                print >> sys.stderr, "You need password for ", src
                dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_OK_CANCEL,
                        _("Enter password:"))
                entry = gtk.Entry()
                entry.set_text(_last_pass)
                entry.show()
                dialog.vbox.pack_end(entry, False, False, 0)
                entry.connect('activate', lambda _: dialog.response(gtk.RESPONSE_OK))
                dialog.set_default_response(gtk.RESPONSE_OK)
                ret = dialog.run()
                text = entry.get_text()
                dialog.destroy()
                if ret == gtk.RESPONSE_OK:
			self._zfile.setpassword(text)
			_last_pass = text
            self._files = self._zfile.namelist()
        elif self._type in (TAR, GZIP, BZIP2):
            self._tfile = tarfile.open(src, 'r')
            self._files = self._tfile.getnames()
        elif self._type == RAR:
            global _rar_exec
            if _rar_exec is None:
                _rar_exec = _get_rar_exec()
                if _rar_exec is None:
                    print '! Could not find RAR file extractor.'
                    dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.WARNING,
                        Gtk.ButtonsType.CLOSE,
                        _("Could not find RAR file extractor!"))
                    dialog.format_secondary_markup(
                        _("You need either the <i>rar</i> or the <i>unrar</i> program installed in order to read RAR (.cbr) files."))
                    dialog.run()
                    dialog.destroy()
                    return None
            need_pass = False
            proc = process.Process([_rar_exec, 'l', '-p-', '--', src])
            fd = proc.spawn()
            for line in fd.readlines():
                if line and line[0] in '*C' and (line.startswith('*') or line.startswith('CRC') or line.startswith('Checksum')):
                    need_pass = True
                    break
            fd.close()
            proc.wait()
            if need_pass:
                print >> sys.stderr, "You need password for ", src
                dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_OK_CANCEL,
                        _("Enter password:"))
                entry = gtk.Entry()
                entry.set_text(_last_pass)
                entry.show()
                dialog.vbox.pack_end(entry, False, False, 0)
                entry.connect('activate', lambda _: dialog.response(gtk.RESPONSE_OK))
                dialog.set_default_response(gtk.RESPONSE_OK)
                ret = dialog.run()
                text = entry.get_text()
                dialog.destroy()
                if ret == gtk.RESPONSE_OK:
                    self._rarpass = '-p' + text
		    _last_pass = text
            proc = process.Process([_rar_exec, 'vb', self._rarpass, '--', src])
            fd = proc.spawn()
            self._files = [name.rstrip(os.linesep) for name in fd.readlines()]
            fd.close()
            proc.wait()
        elif self._type == P7ZIP:
            global _7z_exec
            if _7z_exec is None:
                _7z_exec = _get_7z_exec()
                if _7z_exec is None:
                    print '! Could not find 7z file extractor.'
                    dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_WARNING,
                        gtk.BUTTONS_CLOSE,
                        _("Could not find 7z file extractor!"))
                    dialog.format_secondary_markup(
                        _("You need either the <i>7z</i> or the <i>7za</i> program installed in order to read 7z files."))
                    dialog.run()
                    dialog.destroy()
                    return None
            need_pass = False
            proc = process.Process([_7z_exec, 'l', '-slt', '-p-', src])
            fd = proc.spawn()
            self._files = []
            for line in fd:
                if line.startswith('Path = '):
                    self._files.append(line[7:-1])
                elif line.startswith('Encrypted = +'):
                    need_pass = True
                elif line.endswith('Wrong password?\n'):
                    need_pass = True
                    self._files = []
                    break
            fd.close()
            proc.wait()
            if need_pass:
                print >> sys.stderr, "You need password for ", src
                dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_OK_CANCEL,
                        _("Enter password:"))
                entry = gtk.Entry()
                entry.set_text(_last_pass)
                entry.show()
                dialog.vbox.pack_end(entry, False, False, 0)
                entry.connect('activate', lambda _: dialog.response(gtk.RESPONSE_OK))
                dialog.set_default_response(gtk.RESPONSE_OK)
                ret = dialog.run()
                text = entry.get_text()
                dialog.destroy()
                if ret == gtk.RESPONSE_OK:
                    self._rarpass = '-p' + text
		    _last_pass = text
                    if not self._files:
                        proc = process.Process([_7z_exec, 'l', '-slt', self._rarpass, src])
                        fd = proc.spawn()
                        for line in fd:
                            if line.startswith('Path = '):
                                self._files.append(line[7:-1])
                        fd.close()
                        proc.wait()
        else:
            print '! Non-supported archive format:', src
            return None

        self._setupped = True
        return self._condition

    def get_files(self):
        """Return a list of names of all the files the extractor is currently
        set for extracting. After a call to setup() this is by default all
        files found in the archive. The paths in the list are relative to
        the archive root and are not absolute for the files once extracted.
        """
        return self._files[:]

    def set_files(self, files):
        """Set the files that the extractor should extract from the archive in
        the order of extraction. Normally one would get the list of all files
        in the archive using get_files(), then filter and/or permute this
        list before sending it back using set_files().

        Note: Random access on gzip or bzip2 compressed tar archives is
        no good idea. These formats are supported *only* for backwards
        compability. They are fine formats for some purposes, but should
        not be used for scanned comic books. So, we cheat and ignore the
        ordering applied with this method on such archives.
        """
        if self._type in (GZIP, BZIP2):
            self._files = [x for x in self._files if x in files]
        else:
            self._files = files

    def is_ready(self, name):
        """Return True if the file <name> in the extractor's file list
        (as set by set_files()) is fully extracted.
        """
        return self._extracted.get(name, False)

    def get_mime_type(self):
        """Return the mime type name of the extractor's current archive."""
        return self._type

    def stop(self):
        """Signal the extractor to stop extracting and kill the extracting
        thread. Blocks until the extracting thread has terminated.
        """
        self._stop = True
        if self._setupped:
            self._extract_thread.join()
            self.setupped = False

    def extract(self):
        """Start extracting the files in the file list one by one using a
        new thread. Every time a new file is extracted a notify() will be
        signalled on the Condition that was returned by setup().
        """
        self._extract_thread = threading.Thread(target=self._thread_extract)
        self._extract_thread.setDaemon(False)
        self._extract_thread.start()

    def close(self):
        """Close any open file objects, need only be called manually if the
        extract() method isn't called.
        """
        if self._type == ZIP:
            self._zfile.close()
        elif self._type in (TAR, GZIP, BZIP2):
            self._tfile.close()

    def _thread_extract(self):
        """Extract the files in the file list one by one."""
        for name in self._files:
            self._extract_file(name)
        self.close()

    def _extract_file(self, name):
        """Extract the file named <name> to the destination directory,
        mark the file as "ready", then signal a notify() on the Condition
        returned by setup().
        """
        if self._stop:
            self.close()
            sys.exit(0)
        try:
            if self._type == ZIP:
                dst_path = os.path.join(self._dst, hfs_hack(name))
                if not os.path.exists(os.path.dirname(dst_path)):
                    os.makedirs(os.path.dirname(dst_path))
                new = open(dst_path, 'wb')
                new.write(self._zfile.read(name))
                new.close()
            elif self._type in (TAR, GZIP, BZIP2):
                if os.path.normpath(os.path.join(self._dst, name)).startswith(
                  self._dst):
                    self._tfile.extract(name, self._dst)
                else:
                    print '! Non-local tar member:', name, '\n'
            elif self._type == RAR:
                if _rar_exec is not None:
                    proc = process.Process([_rar_exec, 'x', '-kb', self._rarpass,
                        '-o-', '-inul', '--', self._src, name, self._dst])
                    proc.spawn()
                    proc.wait()
                else:
                    print '! Could not find RAR file extractor.'
            elif self._type == P7ZIP:
                if self.is_ready(name):
                    return
                if _7z_exec is not None:
                    need_bb = False
                    proc = process.Process([_7z_exec, '-h'])
                    fd = proc.spawn()
                    for line in fd.readlines():
                        if line.startswith('  -bb[0-3]'):
                            need_bb = True
                            break
                    fd.close()
                    proc.wait()
                    if not need_bb:
                        proc = process.Process([_7z_exec, 'x', self._rarpass,
                            '-y', '-bd', '-o' + self._dst, self._src]) #, name
                    else:
                        proc = process.Process([_7z_exec, 'x', self._rarpass,
                            '-y', '-bd', '-bb1', '-bse1', '-o' + self._dst, self._src]) #, name
                    fd = proc.spawn()
                    line = fd.readline()
                    count = 0
                    while line:
                        if line.startswith('Extracting  '):
                            self._condition.acquire()
                            fname = line[12:-1]
                            if fname.endswith('     Data Error in encrypted file. Wrong password?'):
                                    fname = fname[:-50]
                            self._extracted[fname] = True
                            rename(self._dst, name)
                            self._condition.notify()
                            self._condition.release()
                            if count == 10:
                                count = 0
                                time.sleep(0.1)
                            else:
                                count += 1
                        elif line.startswith('- ') or line.startswith('T '):
                            self._condition.acquire()
                            fname = line[2:-1]
                            self._extracted[fname] = True
                            rename(self._dst, name)
                            self._condition.notify()
                            self._condition.release()
                            if count == 10:
                                count = 0
                                time.sleep(0.1)
                            else:
                                count += 1
                        line = fd.readline()
                    proc.wait()
                    return
                else:
                    print '! Could not find 7z file extractor.'
        except Exception:
            # Better to ignore any failed extractions (e.g. from a corrupt
            # archive) than to crash here and leave the main thread in a
            # possible infinite block. Damaged or missing files *should* be
            # handled gracefully by the main program anyway.
	    traceback.print_exc()
            pass
        self._condition.acquire()
        self._extracted[name] = True
        rename(self._dst, name)
        self._condition.notify()
        self._condition.release()


class Packer:
    
    """Packer is a threaded class for packing files into ZIP archives.
    
    It would be straight-forward to add support for more archive types,
    but basically all other types are less well fitted for this particular
    task than ZIP archives are (yes, really).
    """
    
    def __init__(self, image_files, other_files, archive_path, base_name):
        """Setup a Packer object to create a ZIP archive at <archive_path>.
        All files pointed to by paths in the sequences <image_files> and
        <other_files> will be included in the archive when packed.
        
        The files in <image_files> will be renamed on the form
        "NN - <base_name>.ext", so that the lexical ordering of their
        filenames match that of their order in the list.
        
        The files in <other_files> will be included as they are,
        assuming their filenames does not clash with other filenames in
        the archive. All files are placed in the archive root.
        """
        self._image_files = image_files
        self._other_files = other_files
        self._archive_path = archive_path
        self._base_name = base_name
        self._pack_thread = None
        self._packing_successful = False

    def pack(self):
        """Pack all the files in the file lists into the archive."""
        self._pack_thread = threading.Thread(target=self._thread_pack)
        self._pack_thread.setDaemon(False)
        self._pack_thread.start()

    def wait(self):
        """Block until the packer thread has finished. Return True if the
        packer finished its work successfully.
        """
        if self._pack_thread != None:
            self._pack_thread.join()
        return self._packing_successful

    def _thread_pack(self):
        try:
            zfile = zipfile.ZipFile(self._archive_path, 'w')
        except Exception:
            print '! Could not create archive', self._archive_path
            return
        used_names = []
        pattern = '%%0%dd - %s%%s' % (len(str(len(self._image_files))),
            self._base_name)
        for i, path in enumerate(self._image_files):
            filename = pattern % (i + 1, os.path.splitext(path)[1])
            try:
                zfile.write(path, filename, zipfile.ZIP_STORED)
            except Exception:
                print '! Could not add file %s to add to %s, aborting...' % (
                    path, self._archive_path)
                zfile.close()
                try:
                    os.remove(self._archive_path)
                except:
                    pass
                return
            used_names.append(filename)
        for path in self._other_files:
            filename = os.path.basename(path)
            while filename in used_names:
                filename = '_%s' % filename
            try:
                zfile.write(path, filename, zipfile.ZIP_DEFLATED)
            except Exception:
                print '! Could not add file %s to add to %s, aborting...' % (
                    path, self._archive_path)
                zfile.close()
                try:
                    os.remove(self._archive_path)
                except:
                    pass
                return
            used_names.append(filename)
        zfile.close()
        self._packing_successful = True


def archive_mime_type(path):
    """Return the archive type of <path> or None for non-archives."""
    try:
        if os.path.isfile(path):
            if not os.access(path, os.R_OK):
                return None
            if zipfile.is_zipfile(path):
                return ZIP
            fd = open(path, 'rb')
            magic = fd.read(4)
            fd.close()
            if tarfile.is_tarfile(path) and os.path.getsize(path) > 0:
                if magic.startswith('BZh'):
                    return BZIP2
                if magic.startswith('\037\213'):
                    return GZIP
                return TAR
            if magic == 'Rar!':
                return RAR
            if magic == '7z\xBC\xAF':
                return P7ZIP
    except Exception:
        print '! Error while reading', path
    return None


def get_name(archive_type):
    """Return a text representation of an archive type."""
    return {ZIP:   _('ZIP archive'),
            TAR:   _('Tar archive'),
            GZIP:  _('Gzip compressed tar archive'),
            BZIP2: _('Bzip2 compressed tar archive'),
            RAR:   _('RAR archive')}[archive_type]


def get_archive_info(path):
    """Return a tuple (mime, num_pages, size) with info about the archive
    at <path>, or None if <path> doesn't point to a supported archive.
    """
    image_re = re.compile(r'\.(jpg|jpeg|png|gif|tif|tiff|bmp)\s*$', re.I)
    extractor = Extractor()
    extractor.setup(path, None)
    mime = extractor.get_mime_type()
    if mime is None:
        return None
    files = extractor.get_files()
    extractor.close()
    num_pages = len(filter(image_re.search, files))
    size = os.stat(path).st_size
    return (mime, num_pages, size)


def _get_rar_exec():
    """Return the name of the RAR file extractor executable, or None if
    no such executable is found.
    """
    for command in ('unrar', 'rar'):
        if process.Process([command]).spawn() is not None:
            return command
    return None

def _get_7z_exec():
    """Return the name of the 7z file extractor executable, or None if
    no such executable is found.
    """
    for command in ('7z', '7za'):
        if process.Process([command]).spawn() is not None:
            return command
    return None

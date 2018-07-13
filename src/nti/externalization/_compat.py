#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System spanning utilities.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

from six import text_type

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3
PYPY = hasattr(sys, 'pypy_version_info')
WIN = sys.platform.startswith("win")
LINUX = sys.platform.startswith('linux')
OSX = sys.platform == 'darwin'


PURE_PYTHON = PYPY or os.getenv('PURE_PYTHON') or os.getenv("NTI_EXT_PURE_PYTHON")


def to_unicode(s, encoding='utf-8', err='strict'):
    """
    Decode a byte sequence and unicode result
    """
    if not isinstance(s, text_type) and s is not None:
        s = s.decode(encoding, err)
    return s

text_ = to_unicode


def bytes_(s, encoding='utf-8', errors='strict'):
    """
    If ``s`` is an instance of ``text_type``, return
    ``s.encode(encoding, errors)``, otherwise return ``s``
    """
    if not isinstance(s, bytes) and s is not None:
        s = s.encode(encoding, errors)
    return s


def import_c_accel(globs, cname):
    """
    Import the C-accelerator for the __name__
    and copy its globals.
    """

    name = globs.get('__name__')

    if not name or name == cname:
        # Do nothing if we're being exec'd as a file (no name)
        # or we're running from the C extension
        return


    if PURE_PYTHON:
        return

    import importlib
    import warnings
    with warnings.catch_warnings():
        # Python 3.7 likes to produce
        # "ImportWarning: can't resolve
        #   package from __spec__ or __package__, falling back on
        #   __name__ and __path__"
        # when we load cython compiled files. This is probably a bug in
        # Cython, but it doesn't seem to have any consequences, it's
        # just annoying to see and can mess up our unittests.
        warnings.simplefilter('ignore', ImportWarning)
        mod = importlib.import_module(cname)

    # By adopting the entire __dict__, we get a more accurate
    # __file__ and module repr, plus we don't leak any imported
    # things we no longer need.
    globs.clear()
    globs.update(mod.__dict__)

    if 'import_c_accel' in globs:
        del globs['import_c_accel']

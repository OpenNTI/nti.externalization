#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System spanning utilities.
"""

import os
import sys
import logging
from typing import overload

text_type = str

WIN = sys.platform.startswith("win")
LINUX = sys.platform.startswith('linux')
OSX = sys.platform == 'darwin'


PURE_PYTHON = os.getenv('PURE_PYTHON') or os.getenv("NTI_EXT_PURE_PYTHON")


try:
    from zope.dublincore.interfaces import IDCTimes # pylint: disable=unused-import
except ModuleNotFoundError:
    from zope.interface import Interface
    #pylint: disable-next=inherit-non-class
    class IDCTimes(Interface): # type:ignore[no-redef]
        """Mock"""

try:
    from ZODB.loglevels import TRACE
except ModuleNotFoundError:
    TRACE = 5
    logging.addLevelName(TRACE, "TRACE")

def to_unicode(s, encoding:str='utf-8', err:str='strict') -> str|None:
    """
    Decode a byte sequence and unicode result
    """
    if not isinstance(s, text_type) and s is not None:
        s = s.decode(encoding, err)
    return s

text_ = to_unicode

@overload
def bytes_(s:str, encoding:str='', errors:str='') -> bytes:
    ...

@overload
def bytes_(s:None, encoding:str='', errors:str='') -> None:
    ...

def bytes_(s, encoding:str='utf-8', errors:str='strict') -> bytes|None:
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

def release_remove_cflags(data): # pragma: no cover pylint:disable=unused-argument
    """
    Strip CFLAGS and other compile settings that
    may not be portable.
    """
    # Especially CFLAGS. If this is compiled in a newer machine with a
    # setting like -march=native, it will produce wheels that won't
    # run on older machines, generating illegal instruction faults.
    for bad_env in (
            'CFLAGS',
            'CPPFLAGS',
            'CXXFLAGS',
            'LDFLAGS',
    ):
        if bad_env in os.environ:
            print("Removing potentially dangerous env setting",
                  bad_env, os.environ[bad_env], file=sys.stderr)
            del os.environ[bad_env]

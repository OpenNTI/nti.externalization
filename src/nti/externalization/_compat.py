#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


if six.PY3:  # pragma: no cover
    def _unicode(s): return str(s)
else:
    _unicode = unicode


def to_unicode(s, encoding='utf-8', err='strict'):
    """
    Decode a byte sequence and unicode result
    """
    s = s.decode(encoding, err) if isinstance(s, bytes) else s
    return _unicode(s) if s is not None else None
text_ = to_unicode


def bytes_(s, encoding='utf-8', errors='strict'):
    """
    If ``s`` is an instance of ``text_type``, return
    ``s.encode(encoding, errors)``, otherwise return ``s``
    """
    if isinstance(s, six.text_type):
        return s.encode(encoding, errors)
    return s


if six.PY3:
    def native_(s, encoding='latin-1', errors='strict'):
        """ 
        If ``s`` is an instance of ``text_type``, return
        ``s``, otherwise return ``str(s, encoding, errors)``
        """
        if isinstance(s, six.text_type):
            return s
        return str(s, encoding, errors)
else:
    def native_(s, encoding='latin-1', errors='strict'):
        """ 
        If ``s`` is an instance of ``text_type``, return
        ``s.encode(encoding, errors)``, otherwise return ``str(s)``
        """
        if isinstance(s, six.text_type):
            return s.encode(encoding, errors)
        return str(s)

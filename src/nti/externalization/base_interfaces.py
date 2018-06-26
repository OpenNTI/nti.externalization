# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Code that is compiled by cython for speed and then exported from
interfaces.py.

This should have no dependencies on things in this package.

This module is **PRIVATE** to this package.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'NotGiven',
    'LocatedExternalDict',
]

class _NotGiven(object):
    """
    A special object you must never pass to any API.
    Used as a marker object for keyword arguments that cannot have the
    builtin None (because that might be a valid value).

    This object is used as-is, it is not instantiated.
    """
    __slots__ = ()

    def __repr__(self):
        return '<default value>'

NotGiven = _NotGiven()

class LocatedExternalDict(dict):
    """
    A dictionary that implements
    :class:`~nti.externalization.interfaces.ILocatedExternalMapping`.
    Returned by
    :func:`~nti.externalization.externalization.to_standard_external_dictionary`.

    This class is not :class:`.IContentTypeAware`, and it indicates so explicitly by declaring a
    `mime_type` value of None.
    """

    # interfaces are applied in interfaces.py

    __slots__ = (
        '__name__',
        '__parent__',
        '__acl__',
        'mimeType',
    )

    def __init__(self, **kwargs):
        # XXX: Do we need to support the possible dictionary constructors?
        dict.__init__(self, **kwargs)
        self.__name__ = u''
        self.__parent__ = None
        self.__acl__ = ()
        self.mimeType = None


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position
import_c_accel(globals(), 'nti.externalization._base_interfaces')

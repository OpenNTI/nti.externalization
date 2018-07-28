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

import numbers
import six

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

    def __repr__(self): # pragma: no cover
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

    def update_from_other(self, other):
        return dict.update(self, other)

def make_external_dict():
    # This layer of indirection is for cython; it can't cimport
    # types when the extension name doesn't match the
    # pxd name. But it can cimport functions that are cpdef to return
    # a type, and then it correctly infers that type for the variable.
    return LocatedExternalDict()


class StandardExternalFields(object):
    """
    Namespace object defining constants whose values are the
    keys used in external mappings.

    These are text (unicode).

    Not all external objects will have all possible keys.
    """
    __slots__ = (
        'ID',
        'OID',
        'HREF',
        'INTID',
        'NTIID',
        'CREATOR',
        'CONTAINER_ID',
        'CREATED_TIME',
        'LAST_MODIFIED',
        'CLASS',
        'LINKS',
        'MIMETYPE',
        'ITEMS',
        'TOTAL',
        'ITEM_COUNT',

        '_ALL_ATTR_NAMES',
        '_ALL_EXTERNAL_KEYS',
    )

    def __init__(self):
        #: An id
        self.ID = u'ID'
        #: An identifier specific to this exact object instance
        self.OID = u'OID'
        #: A hyperlink to reach this object
        self.HREF = u'href'
        #: An integer uniquely identifying the object in some scope
        self.INTID = u'INTID'
        #: A structured identifier similar to a hyperlink
        self.NTIID = u'NTIID'
        #: The name of the creator of the object
        self.CREATOR = u'Creator'
        #: The name of the container holding the object
        self.CONTAINER_ID = u'ContainerId'
        #: The floating point value giving the Unix epoch time
        #: of the object's creation
        self.CREATED_TIME = u'CreatedTime'
        #: The floating point value giving the Unix epoch time
        #: of the last modification of the object
        self.LAST_MODIFIED = u'Last Modified'
        #: 'Class': The class of the object. If the object provides
        #: ``__external_class_name__`` it will be used to populate this.
        self.CLASS = u'Class'
        #: A dictionary mapping "rel" to more hrefs.
        self.LINKS = u'Links'
        #: The MIME type of this object
        self.MIMETYPE = u'MimeType'
        #: A list or dictionary of external objects contained within
        #: this object
        self.ITEMS = u'Items'
        #: A counter
        self.TOTAL = u'Total'
        #: The total number of items contained in this object
        self.ITEM_COUNT = u'ItemCount'

        self._ALL_ATTR_NAMES = frozenset((s for s in StandardExternalFields.__slots__
                                          if not s.startswith('_')))
        self._ALL_EXTERNAL_KEYS = frozenset((getattr(self, s) for s in self._ALL_ATTR_NAMES))

    @property
    def ALL(self):
        return self._ALL_ATTR_NAMES

    @property
    def EXTERNAL_KEYS(self):
        return self._ALL_EXTERNAL_KEYS

_standard_external_fields = StandardExternalFields()

def get_standard_external_fields():
    return _standard_external_fields


#: A set of the external keys (fields) used in
#: minimal external dictionaries. In general,
#: you should prefer StandardExternalFields.EXTERNAL_KEYS
MINIMAL_SYNTHETIC_EXTERNAL_KEYS = frozenset((
    'OID',
    'ID',
    'Last Modified',
    'Creator',
    'ContainerId',
    'Class',
))


def isSyntheticKey(k):
    """
    Deprecated. Prefer to test against StandardExternalFields.EXTERNAL_KEYS
    """
    # pylint:disable=protected-access
    return k in _standard_external_fields._ALL_EXTERNAL_KEYS



class StandardInternalFields(object):
    """
    Namespace object defining constants whose values are the
    property/attribute names looked for on internal objects.

    These must be native strings.
    """

    __slots__ = (
        'ID',
        'NTIID',
        'CREATOR',
        'CREATED_TIME',
        'CONTAINER_ID',
        'LAST_MODIFIED',
        'LAST_MODIFIEDU',
    )

    def __init__(self):
        #: 'id': An object ID
        self.ID = 'id'
        #: 'ntiid': An object's structured ID.
        self.NTIID = 'ntiid'
        #: 'creator': An object that created this object. This will be converted
        #: to a text string to fill in `.StandardExternalFields.CREATOR`.
        self.CREATOR = 'creator'
        #: 'createdTime': The Unix timestamp of the creation of this object.
        #: If no value can be found, we will attempt to adapt to `zope.dublincore.interfaces.IDCTimes`
        #: and use its 'created' attribute. Fills `StandardExternalFields.CREATED_TIME`
        self.CREATED_TIME = 'createdTime'
        #: 'containerId': The ID of the container of this object.
        #: Fills `StandardExternalFields.CONTAINER_ID`.
        self.CONTAINER_ID = 'containerId'
        #: 'lastModified': The Unix timestamp of the last modification of this object.
        #: If no value can be found, we will attempt to adapt to `zope.dublincore.interfaces.IDCTimes`
        #: and use its 'modified' attribute. Fills `.StandardExternalFields.LAST_MODIFIED`
        self.LAST_MODIFIED = 'lastModified'

        self.LAST_MODIFIEDU = 'LastModified'


_standard_internal_fields = StandardInternalFields()

def get_standard_internal_fields():
    return _standard_internal_fields


PRIMITIVES = six.string_types + (numbers.Number, bool, type(None))



from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position
import_c_accel(globals(), 'nti.externalization.__base_interfaces')

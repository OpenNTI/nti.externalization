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

import decimal
import six


__all__ = [
    'NotGiven',
    'LocatedExternalDict',
    'ExternalizationPolicy',
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

dict_init = dict.__init__
dict_update = dict.update

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

    def __init__(self, *args, **kwargs): # pylint:disable=super-init-not-called
        dict_init(self, *args, **kwargs)
        self.__name__ = u''
        self.__parent__ = None
        self.__acl__ = ()
        self.mimeType = None

    def update_from_other(self, other):
        return dict_update(self, other)


def make_external_dict():
    # This layer of indirection is for cython; it can't cimport
    # types when the extension name doesn't match the
    # pxd name. But it can cimport functions that are cpdef to return
    # a type, and then it correctly infers that type for the variable.
    return LocatedExternalDict()


class StandardExternalFields(object):
    """
    Namespace object defining constants whose values are the keys used
    in external mappings.

    These are text (unicode).

    Not all external objects will have all possible keys.

    Two special values are collections of metadata, not strings: `ALL`
    and `EXTERNAL_KEYS`.
    """
    # We're a namespace object, meant to have instance attributes.
    # pylint:disable=too-many-instance-attributes
    __slots__ = (
        'CLASS',
        'CONTAINER_ID',
        'CREATED_TIME',
        'CREATOR',
        'HREF',
        'ID',
        'INTID',
        'ITEMS',
        'ITEM_COUNT',
        'LAST_MODIFIED',
        'LINKS',
        'MIMETYPE',
        'NTIID',
        'OID',
        'TOTAL',

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
        """
        A collection of all *names* of all the attributes of this class.

        That is, the contents of this collection are the attribute names
        that give standard external fields. You can iterate this
        and use :func:`getattr` to get the corresponding values.
        """
        return self._ALL_ATTR_NAMES

    @property
    def EXTERNAL_KEYS(self):
        """
        A collection of all *values* of all attributes of this class.

        That is, the contents of this collection are the keys that
        a standard external object would be expected to have.
        """
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
        #: If no value can be found, we will attempt to adapt to
        #: `zope.dublincore.interfaces.IDCTimes`
        #: and use its 'created' attribute. Fills `StandardExternalFields.CREATED_TIME`
        self.CREATED_TIME = 'createdTime'
        #: 'containerId': The ID of the container of this object.
        #: Fills `StandardExternalFields.CONTAINER_ID`.
        self.CONTAINER_ID = 'containerId'
        #: 'lastModified': The Unix timestamp of the last modification of this object.
        #: If no value can be found, we will attempt to adapt to
        #: zope.dublincore.interfaces.IDCTimes`
        #: and use its 'modified' attribute. Fills `.StandardExternalFields.LAST_MODIFIED`
        self.LAST_MODIFIED = 'lastModified'

        self.LAST_MODIFIEDU = 'LastModified'


_standard_internal_fields = StandardInternalFields()

def get_standard_internal_fields():
    return _standard_internal_fields

# Note that we DO NOT include ``numbers.Number``
# as a primitive type. That's because ``numbers.Number``
# is an ABC and arbitrary types can register as it; but
# arbitrary types are not necessarily understood as proper
# external objects by all representers. In particular,
# ``fractions.Fraction`` cannot be handled by default and
# needs to go through the adaptation process, as does ``complex``.
# simplejson can handle ``decimal.Decimal``, but YAML cannot.
_PRIMITIVE_NUMBER_TYPES = (
    int, # bool is a subclass of int.
    float,
    decimal.Decimal,
)
try:
    long
except NameError:
    pass
else: # Python 2
    _PRIMITIVE_NUMBER_TYPES += (
        long,
    )


PRIMITIVES = six.string_types + (
    type(None),
) + _PRIMITIVE_NUMBER_TYPES


class ExternalizationPolicy(object):
    """
    Adjustment knobs for making tweaks across an entire
    externalization.

    These knobs will tweak low-level details of the externalization
    format, details that are often in a hot code path where overhead
    should be kept to a minimum.

    Instances of this class are used by registering them as named
    components in the global site manager. Certain low-level functions
    accept an optional *policy* argument that must be an instance of this class;
    higher level functions accept a *policy_name* argument that is used to
    find the registered component. If either argument is not given, then
    `DEFAULT_EXTERNALIZATION_POLICY` is used instead.

    Instances are immutable.

    This class must not be subclassed; as such, there is no interface
    for it, merely the class itself.
    """

    __slots__ = (
        'use_iso8601_for_unix_timestamp',
    )

    def __init__(self, use_iso8601_for_unix_timestamp=False):
        #: Should unix timestamp fields be output as their numeric value,
        #: or be converted into an ISO 8601 timestamp string? By default,
        #: the numeric value is output. This is known to specifically apply
        #: to "Created Time" and "Last Modified."
        self.use_iso8601_for_unix_timestamp = use_iso8601_for_unix_timestamp

    def __repr__(self): # pragma: no cover
        return "ExternalizationPolicy(use_iso8601_for_unix_timestamp=%s)" % (
            self.use_iso8601_for_unix_timestamp
        )

#: The default externalization policy.
DEFAULT_EXTERNALIZATION_POLICY = ExternalizationPolicy()

def get_default_externalization_policy():
    return DEFAULT_EXTERNALIZATION_POLICY

from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position
import_c_accel(globals(), 'nti.externalization.__base_interfaces')

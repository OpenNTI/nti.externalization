# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions related to events.

"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from zope.interface import classImplements
from zope.interface import providedBy
from zope.event import notify as _zope_event_notify
from zope.lifecycleevent import IAttributes

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent


logger = __import__('logging').getLogger(__name__)

__all__ = [
    'notifyModified',
]


class _Attributes(object):
    # This is a cython version of zope.lifecycleevent.Attributes
    # for faster instantiation and collection of attrs

    __slots__ = (
        'interface',
        'attributes',
    )

    def __init__(self, iface):
        self.interface = iface
        self.attributes = set()

classImplements(_Attributes, IAttributes)

def _make_modified_attributes(containedObject, external_keys):
    # TODO: Share the interface cache from datastructures.
    # {iface -> _Attributes(iface)}
    attributes = {}
    provides = providedBy(containedObject)
    get_iface = provides.get
    for k in external_keys:
        iface_providing_attr = None
        iface_attr = get_iface(k)
        if iface_attr is not None:
            iface_providing_attr = iface_attr.interface

        try:
            attrs = attributes[iface_providing_attr]
        except KeyError:
            attrs = attributes[iface_providing_attr] = _Attributes(iface_providing_attr)

        attrs.attributes.add(k)

    return attributes.values()

def _make_modified_event(containedObject, externalObject, updater,
                         attributes, kwargs):
    event = ObjectModifiedFromExternalEvent(containedObject, *attributes, **kwargs)
    event.external_value = externalObject
    # Let the updater have its shot at modifying the event, too, adding
    # interfaces or attributes. (Note: this was added to be able to provide
    # sharedWith information on the event, since that makes for a better stream.
    # If that use case expands, revisit this interface.
    # XXX: Document and test this.
    try:
        meth = updater._ext_adjust_modified_event # pylint:disable=protected-access
    except AttributeError:
        pass
    else:
        event = meth(event) # pragma: no cover

    return event

def _notifyModified(containedObject, externalObject, updater, external_keys,
                    kwargs):
    # try to provide external keys
    if external_keys is None:
        external_keys = list(externalObject.keys())

    # TODO: We need to try to find the actual interfaces and fields to allow correct
    # decisions to be made at higher levels.
    # zope.formlib.form.applyData does this because it has a specific, configured mapping. We
    # just do the best we can by looking at what's implemented. The most specific
    # interface wins
    # map from interface class to list of keys
    attributes = _make_modified_attributes(containedObject, external_keys)
    event = _make_modified_event(containedObject, externalObject, updater,
                                 attributes, kwargs)
    _zope_event_notify(event)
    return event

def notifyModified(containedObject, externalObject, updater=None, external_keys=None,
                   **kwargs):
    return _notifyModified(containedObject, externalObject, updater, external_keys,
                           kwargs)


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._events')

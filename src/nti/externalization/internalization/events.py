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
from nti.externalization._interface_cache import cache_for_key

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
    cache = cache_for_key(_Attributes, containedObject)
    # {'attrname': Interface}
    attr_to_iface = cache.modified_event_attributes

    # Ensure that each attribute name in *names* is
    # in the _v_attrs dict of *provides*. Also
    # makes sure that self.attr_to_iface maps each
    # name to its interface.
    # Returns a sequence of fresh _Attributes objects.
    provides = providedBy(containedObject)
    # {iface -> _Attributes(iface)}
    result = {}
    # By the time we get here, we're guaranteed that
    # _v_attrs exists---it's where we're cached
    attrs = provides._v_attrs # pylint:disable=protected-access

    for name in external_keys:
        # This is the core loop of provides.get()
        # (z.i.declaration.Declaration.get)
        attr = attrs.get(name, cache)
        # Steady state, misses are rare here.
        if attr is cache:
            for iface in provides.__iro__:
                attr = iface.direct(name)
                if attr is not None:
                    attrs[name] = attr
                    break
            else:
                # Not part of any interface
                attr = attrs[name] = None

        providing_iface = attr_to_iface.get(name, cache)
        if providing_iface is cache:
            # In the steady state, misses should be rare here.
            providing_iface = None
            if attr is not None:
                providing_iface = attr.interface
            attr_to_iface[name] = providing_iface



        attributes = result.get(providing_iface)
        if attributes is None:
            # Misses aren't unexpected here. often attributes
            # are spread across multiple interfaces
            attributes = result[providing_iface] = _Attributes(providing_iface)

        attributes.attributes.add(name)

    return result.values()


def _make_modified_event(containedObject, externalObject, updater,
                         attributes, kwargs):
    event = ObjectModifiedFromExternalEvent(containedObject, *attributes, **kwargs)
    event.external_value = externalObject
    # Let the updater have its shot at modifying the event, too, adding
    # interfaces or attributes. (Note: this was added to be able to provide
    # sharedWith information on the event, since that makes for a better stream.
    # If that use case expands, revisit this interface.)
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
    """
    Create and send an `~.ObjectModifiedFromExternalEvent` for
    *containedObject* using `zope.event.notify`.

    The *containedObject* is the subject of the event. The
    *externalObject* is the dictionary of data that was used to update
    the *containedObject*.

    *external_keys* is list of keys from *externalObject* that
    actually changed *containedObject*. If this is not given, we
    assume that all keys in *externalObject* were changed. Note that
    these should to correspond to the interface fields of interfaces
    that the *containedObject* implements in order to properly be able
    to create and populate the `zope.lifecycleevent` `~zope.lifecycleevent.IAttributes`.

    *updater*, if given, is the `~nti.externalization.interfaces.IInternalObjectUpdater`
    instance that was used to handle the updates. If this object implements
    an ``_ext_adjust_modified_event`` method, it will be called to adjust (and return)
    the event object that will be notified.

    *kwargs* are the keyword arguments passed to the event constructor.

    :return: The event object that was notified.
    """

    return _notifyModified(containedObject, externalObject, updater, external_keys,
                           kwargs)


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._events')

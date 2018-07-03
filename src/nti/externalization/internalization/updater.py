# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
The driver functions for updating an object from an external form.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# stdlib imports
from collections import MutableSequence
from collections import MutableMapping
import inspect
import warnings

from persistent.interfaces import IPersistent
from six import iteritems
from zope import component

from nti.externalization._base_interfaces import PRIMITIVES
from nti.externalization.interfaces import IInternalObjectUpdater

from .factories import find_factory_for
from .events import _notifyModified
from .externals import resolve_externals



_EMPTY_DICT = {}
IPersistent_providedBy = IPersistent.providedBy

class _RecallArgs(object):
    __slots__ = (
        'registry',
        'context',
        'require_updater',
        'notify',
        'pre_hook',
    )

    def __init__(self, registry,
                 context,
                 require_updater,
                 notify,
                 pre_hook):
        self.registry = registry
        self.context = context
        self.require_updater = require_updater
        self.notify = notify
        self.pre_hook = pre_hook


def _recall(k, obj, ext_obj, kwargs):
    # We must manually pass all the args to get the optimized
    # cython call
    obj = update_from_external_object(obj, ext_obj,
                                      registry=kwargs.registry,
                                      context=kwargs.context,
                                      require_updater=kwargs.require_updater,
                                      notify=kwargs.notify,
                                      pre_hook=kwargs.pre_hook)
    if IPersistent_providedBy(obj): # pragma: no cover
        obj._v_updated_from_external_source = ext_obj
    return obj


def update_from_external_object(containedObject, externalObject,
                                registry=component, context=None,
                                require_updater=False,
                                notify=True,
                                pre_hook=None):
    """
    Central method for updating objects from external values.

    :param containedObject: The object to update.
    :param externalObject: The object (typically a mapping or sequence) to update
        the object from. Usually this is obtained by parsing an external
        format like JSON.
    :param context: An object passed to the update methods.
    :param require_updater: If True (not the default) an exception
        will be raised if no implementation of
        :class:`~nti.externalization.interfaces.IInternalObjectUpdater`
        can be found for the `containedObject.`
    :keyword bool notify: If ``True`` (the default), then if the updater
        for the `containedObject` either has no preference (returns
        None) or indicates that the object has changed, then an
        :class:`~nti.externalization.interfaces.IObjectModifiedFromExternalEvent`
        will be fired. This may be a recursive process so a top-level
        call to this object may spawn multiple events. The events that
        are fired will have a ``descriptions`` list containing one or
        more :class:`~zope.lifecycleevent.interfaces.IAttributes` each
        with ``attributes`` for each attribute we modify (assuming
        that the keys in the ``externalObject`` map one-to-one to an
        attribute; if this is the case and we can also find an
        interface declaring the attribute, then the ``IAttributes``
        will have the right value for ``interface`` as well).
    :keyword callable pre_hook: If given, called with the before
        update_from_external_object is called for every nested object.
        Signature ``f(k,x)`` where ``k`` is either the key name, or
        None in the case of a sequence and ``x`` is the external
        object. Deprecated.
    :return: `containedObject` after updates from `externalObject`

    .. versionchanged:: 1.0.0a2
       Remove the ``object_hook`` parameter.
    """

    if pre_hook is not None: # pragma: no cover
        for i in range(3):
            warnings.warn('pre_hook is deprecated', FutureWarning, stacklevel=i)

    kwargs = _RecallArgs(
        registry,
        context,
        require_updater,
        notify,
        pre_hook
    )


    # Parse any contained objects
    # TODO: We're (deliberately?) not actually updating any contained
    # objects, we're replacing them. Is that right? We could check OIDs...
    # If we decide that's right, then the internals could be simplified by
    # splitting the two parts
    # TODO: Schema validation
    # TODO: Should the current user impact on this process?

    # Sequences do not represent python types, they represent collections of
    # python types
    if isinstance(externalObject, MutableSequence):
        tmp = []
        for value in externalObject:
            if pre_hook is not None: # pragma: no cover
                pre_hook(None, value)
            factory = find_factory_for(value, registry=registry)
            tmp.append(_recall(None, factory(), value, kwargs) if factory is not None else value)
        # XXX: TODO: Should we be assigning this to the slice of externalObject?
        # in-place?
        return tmp

    assert isinstance(externalObject, MutableMapping)

    # We have to save the list of keys, it's common that they get popped during the update
    # process, and then we have no descriptions to send
    external_keys = list()
    for k, v in iteritems(externalObject):
        external_keys.append(k)
        if isinstance(v, PRIMITIVES):
            continue

        if pre_hook is not None: # pragma: no cover
            pre_hook(k, v)

        if isinstance(v, MutableSequence):
            # Update the sequence in-place
            # XXX: This is not actually updating it.
            # We need to slice externalObject[k[:]]
            __traceback_info__ = k, v
            v = _recall(k, (), v, kwargs)
            externalObject[k] = v
        else:
            factory = find_factory_for(v, registry=registry)
            if factory is not None:
                externalObject[k] = _recall(k, factory(), v, kwargs)

    updater = None
    if hasattr(containedObject, 'updateFromExternalObject') \
        and not getattr(containedObject, '__ext_ignore_updateFromExternalObject__', False):
        # legacy support. The __ext_ignore_updateFromExternalObject__
        # allows a transition to an adapter without changing
        # existing callers and without triggering infinite recursion
        updater = containedObject
    else:
        if require_updater:
            get = registry.getAdapter
        else:
            get = registry.queryAdapter

        updater = get(containedObject, IInternalObjectUpdater)

    if updater is not None:
        # Let the updater resolve externals too
        resolve_externals(updater, containedObject, externalObject,
                          registry=registry, context=context)

        updated = None
        # The signature may vary.
        # XXX: This is slow and cumbersome and needs to go.
        # See https://github.com/NextThought/nti.externalization/issues/30
        try:
            argspec = inspect.getargspec(updater.updateFromExternalObject)
        except TypeError: # pragma: no cover (This is hard to catch in pure-python coverage mode)
            # Cython functions and other extension types are "not a Python function"
            # and don't work with this. We assume they use the standard form accepting
            # 'context' as kwarg
            updated = updater.updateFromExternalObject(externalObject, context=context)
        else:
            if 'context' in argspec.args or (argspec.keywords and 'dataserver' not in argspec.args):
                updated = updater.updateFromExternalObject(externalObject,
                                                           context=context)
            elif argspec.keywords or 'dataserver' in argspec.args:
                updated = updater.updateFromExternalObject(externalObject,
                                                           dataserver=context)
            else:
                updated = updater.updateFromExternalObject(externalObject)

        # Broadcast a modified event if the object seems to have changed.
        if notify and (updated is None or updated):
            _notifyModified(containedObject, externalObject,
                            updater, external_keys, _EMPTY_DICT)

    return containedObject


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._updater')

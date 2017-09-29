#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions for dealing with persistence in an external context.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import collections

import persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from persistent.wref import WeakRef as PWeakRef
from six import iteritems
from zope import interface

from nti.externalization.datastructures import ExternalizableDictionaryMixin
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import IExternalObject
from nti.externalization.oids import toExternalOID
from nti.externalization.proxy import removeAllProxies


# disable: accessing protected members
# pylint: disable=W0212


def getPersistentState(obj):
    """
    For a :class:`persistent.Persistent` object, returns one of the
    constants from the persistent module for its state:
    :const:`persistent.CHANGED` and :const:`persistent.UPTODATE` being the most useful.

    If the object is not Persistent and doesn't implement a ``getPersistentState`` method,
    this method will be pessimistic and assume the object has
    been :const:`persistent.CHANGED`.
    """
    # Certain types of proxies are also Persistent and maintain a state separate from
    # their wrapped object, notably zope.container.contained.ContainedProxy, as used
    # in certain containers (such usage is generally deprecated now).
    # To meet our pessimistic requirement, we will report changed if either the proxy
    # or the wrapped object does

    try:
        # Trust the changed value ahead of the state value,
        # because it is settable from python but the state
        # is more implicit.
        return persistent.CHANGED if obj._p_changed else persistent.UPTODATE
    except AttributeError:
        pass

    try:
        if obj._p_state == persistent.UPTODATE and obj._p_jar is None:
            # In keeping with the pessimistic theme, if it claims to be uptodate, but has never
            # been saved, we consider that the same as changed
            return persistent.CHANGED
    except AttributeError:
        pass

    unwrapped = removeAllProxies(obj)
    if unwrapped is not obj:
        return getPersistentState(unwrapped)

    try:
        return obj._p_state
    except AttributeError:
        try:
            return obj.getPersistentState()
        except AttributeError:
            return persistent.CHANGED


def setPersistentStateChanged(obj):
    """
    Explicitly marks a persistent object as changed.
    """
    try:
        obj._p_changed = True
    except AttributeError:
        pass


def _weakRef_toExternalObject(self):
    val = self()
    if val is not None:
        return toExternalObject(val)
PWeakRef.toExternalObject = _weakRef_toExternalObject
interface.classImplements(PWeakRef, IExternalObject)


def _weakRef_toExternalOID(self):
    val = self()
    if val is not None:
        return toExternalOID(val)
PWeakRef.toExternalOID = _weakRef_toExternalOID


class PersistentExternalizableDictionary(PersistentMapping,
                                         ExternalizableDictionaryMixin):
    """
    Dictionary mixin that provides :meth:`toExternalDictionary` to
    return a new dictionary with each value in the dict having been
    externalized with :func:`~.toExternalObject`.

    .. versionchanged:: 1.0
        No longer extends :class:`nti.zodb.persistentproperty.PersistentPropertyHolder`.
        If you have subclasses that use writable properties and which should
        bypass the normal attribute setter implementation, please
        mixin this superclass (first) yourself.
    """

    def toExternalDictionary(self, *args, **kwargs):
        result = super(PersistentExternalizableDictionary, self).toExternalDictionary(self, *args, **kwargs)
        for key, value in iteritems(self):
            result[key] = toExternalObject(value, *args, **kwargs)
        return result


class PersistentExternalizableList(PersistentList):
    """
    List mixin that provides :meth:`toExternalList` to return a new list
    with each element in the sequence having been externalized with
    :func:`~.toExternalObject`.


    .. versionchanged:: 1.0
        No longer extends :class:`nti.zodb.persistentproperty.PersistentPropertyHolder`.
        If you have subclasses that use writable properties and which should
        bypass the normal attribute setter implementation, please
        mixin this superclass (first) yourself.
    """

    def toExternalList(self):
        result = [toExternalObject(x) for x in self if x is not None]
        return result

    def values(self):
        """
        For compatibility with :mod:`zope.generations.utility`, this object
        defines a `values` method which does nothing but return itself. That
        makes these objects transparent and suitable for migrations.
        """
        return self


class PersistentExternalizableWeakList(PersistentExternalizableList):
    """
    Stores :class:`persistent.Persistent` objects as weak references,
    invisibly to the user. Any weak references added to the list will
    be treated the same.

    Weak references are resolved on access; if the referrant has been
    deleted, then that access will return ``None``.

    .. versionchanged:: 1.0
        No longer extends :class:`nti.zodb.persistentproperty.PersistentPropertyHolder`.
        If you have subclasses that use writable properties and which should
        bypass the normal attribute setter implementation, please
        mixin this superclass (first) yourself.
    """

    def __init__(self, initlist=None):
        if initlist is not None:
            initlist = [self.__wrap(x) for x in initlist]
        super(PersistentExternalizableWeakList, self).__init__(initlist)

    def __getitem__(self, i):
        return super(PersistentExternalizableWeakList, self).__getitem__(i)()

    # NOTE: __iter__ is implemented with __getitem__ so we don't reimplement.
    # However, __eq__ isn't, it wants to directly compare lists
    def __eq__(self, other):
        # If we just compare lists, weak refs will fail badly
        # if they're compared with non-weak refs
        if not isinstance(other, collections.Sequence):
            return False

        result = False
        if len(self) == len(other):
            result = True
            for i in range(len(self)):
                if self[i] != other[i]:
                    result = False
                    break
        return result

    def __wrap(self, obj):
        return obj if isinstance(obj, PWeakRef) else PWeakRef(obj)

    def remove(self, value):
        super(PersistentExternalizableWeakList, self).remove(self.__wrap(PWeakRef(value)))

    def __setitem__(self, i, item):
        super(PersistentExternalizableWeakList, self).__setitem__(i, self.__wrap(PWeakRef(item)))

    def __setslice__(self, i, j, other):
        raise TypeError('Not supported')  # pragma: no cover

    # Unfortunately, these are not implemented in terms of the primitives, so
    # we need to overide each one. They can throw exceptions, so we're careful
    # not to prematurely update lastMod

    def __iadd__(self, other):
        # We must wrap each element in a weak ref
        # Note that the builtin list only accepts other lists,
        # but the UserList from which we are descended accepts
        # any iterable.
        result = super(PersistentExternalizableWeakList, self).__iadd__([self.__wrap(PWeakRef(o)) for o in other])
        return result

    def __imul__(self, n):
        result = super(PersistentExternalizableWeakList, self).__imul__(n)
        return result

    def append(self, item):
        super(PersistentExternalizableWeakList, self).append(self.__wrap(PWeakRef(item)))

    def insert(self, i, item):
        super(PersistentExternalizableWeakList, self).insert(i, self.__wrap(PWeakRef(item)))

    def pop(self, i=-1):
        rtn = super(PersistentExternalizableWeakList, self).pop(i)
        return rtn()

    def extend(self, other):
        for x in other:
            self.append(x)

    def count(self, item):
        return super(PersistentExternalizableWeakList, self).count(self.__wrap(PWeakRef(item)))

    def index(self, item, *args):
        return super(PersistentExternalizableWeakList, self).index(self.__wrap(PWeakRef(item)), *args)


def NoPickle(cls):
    """
    A class decorator that prevents an object
    from being pickled. Useful for ensuring certain
    objects do not get pickled and thus avoiding
    ZODB backward compatibility concerns.

    .. warning:: If you subclass something that used this
            decorator, you should override ``__reduce_ex__``
            (or both it and ``__reduce__``).

    """

    msg = "Not allowed to pickle %s" % cls

    def __reduce_ex__(self, protocol=0):
        raise TypeError(msg)

    __reduce__ = __reduce_ex__

    cls.__reduce__ = __reduce__
    cls.__reduce_ex__ = __reduce_ex__

    return cls

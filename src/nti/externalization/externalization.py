# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Functions related to actually externalizing objects.

.. $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
from calendar import timegm as _calendar_gmtime
import collections
from collections import defaultdict
import numbers
import warnings

import BTrees.OOBTree
from ZODB.POSException import POSKeyError
import persistent
import six
from six import text_type


from zope import component
from zope import interface

from zope.dublincore.interfaces import IDCTimes
from zope.interface.common.sequence import IFiniteSequence
from zope.security.interfaces import IPrincipal
from zope.security.management import system_user

from nti.externalization._compat import identity
from nti.externalization._threadlocal import ThreadLocalManager
from nti.externalization.extension_points import get_current_request
from nti.externalization.extension_points import set_external_identifiers
from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import ILocatedExternalSequence
from nti.externalization.interfaces import INonExternalizableReplacement
from nti.externalization.interfaces import INonExternalizableReplacer
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import StandardInternalFields


logger = __import__('logging').getLogger(__name__)

# Local for speed
StandardExternalFields_ID = StandardExternalFields.ID
StandardExternalFields_OID = StandardExternalFields.OID
StandardExternalFields_CLASS = StandardExternalFields.CLASS
StandardExternalFields_NTIID = StandardExternalFields.NTIID
StandardExternalFields_CREATOR = StandardExternalFields.CREATOR
StandardExternalFields_MIMETYPE = StandardExternalFields.MIMETYPE
StandardExternalFields_CONTAINER_ID = StandardExternalFields.CONTAINER_ID
StandardExternalFields_CREATED_TIME = StandardExternalFields.CREATED_TIME
StandardExternalFields_LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

StandardInternalFields_ID = StandardInternalFields.ID
StandardInternalFields_CREATOR = StandardInternalFields.CREATOR
StandardInternalFields_CONTAINER_ID = StandardInternalFields.CONTAINER_ID
StandardInternalFields_CREATED_TIME = StandardInternalFields.CREATED_TIME
StandardInternalFields_LAST_MODIFIED = StandardInternalFields.LAST_MODIFIED
StandardInternalFields_LAST_MODIFIEDU = StandardInternalFields.LAST_MODIFIEDU

SYSTEM_USER_NAME = getattr(system_user, 'title').lower()


def is_system_user(obj):
    return IPrincipal.providedBy(obj) and obj.id == system_user.id

_NotGiven = object()

# It turns out that the name we use for externalization (and really the registry, too)
# we must keep thread-local. We call into objects without any context,
# and they call back into us, and otherwise we would lose
# the name that was established at the top level.
_manager = ThreadLocalManager(default=lambda: {'name': _NotGiven, 'memos': None})

# Things that can be directly externalized
_primitives = six.string_types + (numbers.Number, bool)


def catch_replace_action(obj, exc):
    """
    Replaces the external component object `obj` with an object noting a broken object.
    """
    __traceback_info__ = obj, exc
    return {"Class": "BrokenExceptionObject"}


@interface.implementer(INonExternalizableReplacement)
class _NonExternalizableObject(dict):
    pass


def DefaultNonExternalizableReplacer(obj):
    logger.debug("Asked to externalize non-externalizable object %s, %s",
                 type(obj), obj)
    result = _NonExternalizableObject(Class='NonExternalizableObject',
                                      InternalType=str(type(obj)))
    return result


class NonExternalizableObjectError(TypeError):
    pass


def DevmodeNonExternalizableObjectReplacer(obj):
    """
    When devmode is active, non-externalizable objects raise an exception.
    """
    raise NonExternalizableObjectError("Asked to externalize non-externalizable object %s, %s" %
                                       (type(obj), obj))


@interface.implementer(INonExternalizableReplacer)
def _DevmodeNonExternalizableObjectReplacer(_):
    return DevmodeNonExternalizableObjectReplacer


#: The types that we will treat as sequences for externalization purposes. These
#: all map onto lists. (TODO: Should we just try to iter() it, ignoring strings?)
#: In addition, we also support :class:`~zope.interface.common.sequence.IFiniteSequence`
#: by iterating it and mapping onto a list. This allows :class:`~z3c.batching.interfaces.IBatch`
#: to be directly externalized.
SEQUENCE_TYPES = (persistent.list.PersistentList,
                  collections.Set,
                  list,
                  tuple)

#: The types that we will treat as mappings for externalization purposes. These
#: all map onto a dict.
MAPPING_TYPES = (persistent.mapping.PersistentMapping,
                 BTrees.OOBTree.OOBTree,
                 collections.Mapping)



class _ExternalizationState(object):

    name = u''
    request = None
    registry = None
    # We take a similar approach to pickle.Pickler
    # for memoizing objects we've seen:
    # we map the id of an object to a two tuple: (obj, external-value)
    # the original object is kept in the tuple to keep transient objects alive
    # and thus ensure no overlapping ids
    memo = None

    def __init__(self, memos, kwargs):
        self.__dict__.update(kwargs)
        self.memo = memos[self.name]

class _RecursiveCallState(dict):
    pass


_marker = object()


def _to_external_object_state(obj, state, top_level=False, decorate=True,
                              useCache=True, decorate_callback=_NotGiven):
    __traceback_info__ = obj

    orig_obj = obj
    orig_obj_id = id(obj) # XXX: Relatively expensive on PyPy
    if useCache:
        value = state.memo.get(orig_obj_id, None)
        result = value[1] if value is not None else None
        if result is None:  # mark as in progress
            state.memo[orig_obj_id] = (orig_obj, _marker)
        elif result is not _marker:
            return result
        elif obj is not None:
            logger.warn("Recursive call to object %s.", obj)
            result = to_standard_external_dictionary(obj,
                                                     decorate=False)

            return _RecursiveCallState(result)

    try:
        # TODO: This is needless for the mapping types and sequence types. rework to avoid.
        # Benchmarks show that simply moving it into the last block doesn't actually save much
        # (due to all the type checks in front of it?)

        # This is for legacy code support, to allow existing methods to move to adapters
        # and call us without infinite recursion
        obj_has_usable_external_object = \
            hasattr(obj, 'toExternalObject') \
            and not getattr(obj, '__ext_ignore_toExternalObject__', False)

        if not obj_has_usable_external_object and not IExternalObject.providedBy(obj):
            adapter = state.registry.queryAdapter(obj, IExternalObject, default=None,
                                                  name=state.name)
            if not adapter and state.name != '':
                # try for the default, but allow passing name of None to
                # disable (?)
                adapter = state.registry.queryAdapter(obj, IExternalObject,
                                                      default=None, name='')
            if adapter:
                obj = adapter
                obj_has_usable_external_object = True

        # Note that for speed, before calling 'recall' we are performing the
        # primitive check
        result = obj
        if obj_has_usable_external_object:  # either an adapter or the original object
            result = obj.toExternalObject(request=state.request, name=state.name,
                                          decorate=decorate, useCache=useCache,
                                          decorate_callback=decorate_callback)
        elif hasattr(obj, "toExternalDictionary"):
            result = obj.toExternalDictionary(request=state.request, name=state.name,
                                              decorate=decorate, useCache=useCache,
                                              decorate_callback=decorate_callback)
        elif hasattr(obj, "toExternalList"):
            result = obj.toExternalList()
        elif isinstance(obj, MAPPING_TYPES):
            # XXX: This winds up calling decorate_callback at least twice.
            result = to_standard_external_dictionary(obj,
                                                     registry=state.registry,
                                                     request=state.request,
                                                     decorate=decorate,
                                                     decorate_callback=decorate_callback)
            if obj.__class__ is dict:
                result.pop('Class', None)
            # Note that we recurse on the original items, not the things newly added.
            # NOTE: This means that Links added here will not be externalized. There
            # is an IExternalObjectDecorator that does that
            for key, value in obj.items():
                if not isinstance(value, _primitives):
                    ext_obj = _to_external_object_state(value, state,
                                                        top_level=False,
                                                        decorate=decorate,
                                                        useCache=useCache,
                                                        decorate_callback=decorate_callback)
                else:
                    ext_obj = value
                result[key] = ext_obj

        elif isinstance(obj, SEQUENCE_TYPES) or IFiniteSequence.providedBy(obj):
            result = []
            for value in obj:
                if not isinstance(value, _primitives):
                    ext_obj = _to_external_object_state(value, state,
                                                        top_level=False,
                                                        decorate=decorate,
                                                        useCache=useCache,
                                                        decorate_callback=decorate_callback)
                else:
                    ext_obj = value
                result.append(ext_obj)
            result = state.registry.getAdapter(result,
                                               ILocatedExternalSequence)
        elif obj is not None:
            # Otherwise, we probably won't be able to JSON-ify it.
            # TODO: Should this live here, or at a higher level where the ultimate
            # external target/use-case is known?
            replacer = state.default_non_externalizable_replacer
            result = state.registry.queryAdapter(obj, INonExternalizableReplacer,
                                                 default=replacer)(obj)

        if decorate:
            for decorator in state.registry.subscribers((orig_obj,), IExternalObjectDecorator):
                decorator.decorateExternalObject(orig_obj, result)
        elif callable(decorate_callback):
            decorate_callback(orig_obj, result)

        # Request specific decorating, if given, is more specific than plain object
        # decorating, so it gets to go last.
        if decorate and state.request is not None and state.request is not _NotGiven:
            for decorator in state.registry.subscribers((orig_obj, state.request),
                                                        IExternalObjectDecorator):
                decorator.decorateExternalObject(orig_obj, result)

        if useCache:  # save result
            state.memo[orig_obj_id] = (orig_obj, result)
        return result
    except state.catch_components as t:
        if top_level:
            raise
        # python rocks. catch_components could be an empty tuple, meaning we catch nothing.
        # or it could be any arbitrary list of exceptions.
        # NOTE: we cannot try to to-string the object, it may try to call back to us
        # NOTE2: In case we encounter a proxy (zope.container.contained.ContainedProxy)
        # the type(o) is not reliable. Only the __class__ is.
        # NOTE3: On Cython 0.28.3 on Python 3, this actually fails.
        # We expect to see this bug fixed before we release.
        # https://github.com/cython/cython/issues/2425
        logger.exception("Exception externalizing component object %s/%s",
                         type(obj), obj.__class__)
        return state.catch_component_action(obj, t)



def toExternalObject(obj,
                     name=_NotGiven,
                     registry=component,
                     catch_components=(),
                     catch_component_action=None,
                     request=_NotGiven,
                     decorate=True,
                     useCache=True,
                     # XXX: Why do we have this? It's only used when decotare is False,
                     # which doesn't make much sense.
                     decorate_callback=_NotGiven,
                     default_non_externalizable_replacer=DefaultNonExternalizableReplacer):
    """
    Translates the object into a form suitable for
    external distribution, through some data formatting process. See :const:`SEQUENCE_TYPES`
    and :const:`MAPPING_TYPES` for details on what we can handle by default.

    :param string name: The name of the adapter to :class:IExternalObject to look
        for. Defaults to the empty string (the default adapter). If you provide
        a name, and an adapter is not found, we will still look for the default name
        (unless the name you supply is None).
    :param tuple catch_components: A tuple of exception classes to catch when
        externalizing sub-objects (e.g., items in a list or dictionary). If one of these
        exceptions is caught, then `catch_component_action` will be called to raise or replace
        the value. The default is to catch nothing.
    :param callable catch_component_action: If given with `catch_components`, a function
        of two arguments, the object being externalized and the exception raised. May return
        a different object (already externalized) or re-raise the exception. There is no default,
        but :func:`catch_replace_action` is a good choice.
    :param callable default_non_externalizable_replacer: If we are asked to externalize an object
        and cannot, and there is no :class:`~nti.externalization.interfaces.INonExternalizableReplacer` registered for it,
        then call this object and use the results.
    :param request: If given, the request that the object is being externalized on behalf
        of. If given, then the object decorators will also look for subscribers
        to the object plus the request (like traversal adapters); this is a good way to
        separate out request or user specific code.
    :param decorate_callback: Callable to be invoked in case there is no decaration
    """

    # Catch the primitives up here, quickly
    if isinstance(obj, _primitives):
        return obj

    if name is _NotGiven:
        name = _manager.get()['name']
    if name is _NotGiven:
        name = ''
    if request is _NotGiven:
        request = get_current_request()

    memos = _manager.get()['memos']
    if memos is None:
        memos = defaultdict(dict)

    v = dict(locals())
    v.pop('obj')
    v.pop("memos")
    state = _ExternalizationState(memos, v)

    _manager.push({'name': name, 'memos': memos})

    try:
        return _to_external_object_state(obj, state, top_level=True,
                                         decorate=decorate, useCache=useCache,
                                         decorate_callback=decorate_callback)
    finally:
        _manager.pop()
to_external_object = toExternalObject



def stripSyntheticKeysFromExternalDictionary(external):
    """
    Given a mutable dictionary, removes all the external keys
    that might have been added by :func:`to_standard_external_dictionary` and echoed back.
    """
    for key in _syntheticKeys():
        external.pop(key, None)
    return external

_SYNTHETIC_KEYS = frozenset(('OID', 'ID', 'Last Modified', 'Creator',
                             'ContainerId', 'Class'))

def _syntheticKeys():
    # XXX: Why is this a callable?
    return _SYNTHETIC_KEYS

def _isMagicKey(key):
    """
    For our mixin objects that have special keys, defines
    those keys that are special and not settable by the user.
    """
    return key in _SYNTHETIC_KEYS
isSyntheticKey = _isMagicKey




def datetime_to_epoch(dt):
    return _calendar_gmtime(dt.utctimetuple()) if dt is not None else None
_datetime_to_epoch = datetime_to_epoch


def choose_field(result, self, ext_name,
                 converter=identity,
                 fields=(),
                 sup_iface=None, sup_fields=(), sup_converter=identity):
    # XXX: We have a public user of this in nti.ntiids.oids. We need
    # to document this and probably move it to a different module, or
    # provide a cleaner simpler replacement.
    for x in fields:
        try:
            value = getattr(self, x)
        except AttributeError:
            continue
        except POSKeyError:
            logger.exception("Could not get attribute %s for object %s",
                             x, self)
            continue

        if value is not None:
            # If the creator is the system user, catch it here
            # XXX: Document this behaviour.
            if ext_name == StandardExternalFields_CREATOR:
                if is_system_user(value):
                    value = SYSTEM_USER_NAME
                else:
                    # This is a likely recursion point, we want to be
                    # sure we don't do that.
                    value = text_type(value)
                result[ext_name] = value
                return value
            value = converter(value)
            if value is not None:
                result[ext_name] = value
                return value

    # Nothing. Can we adapt it?
    if sup_iface is not None and sup_fields:
        self = sup_iface(self, None)
        if self is not None:
            return choose_field(result, self, ext_name,
                                converter=sup_converter,
                                fields=sup_fields)


def to_standard_external_last_modified_time(context, default=None, _write_into=None):
    """
    Find and return a number representing the time since the epoch
    in fractional seconds at which the ``context`` was last modified.
    This is the same value that is used by :func:`to_standard_external_dictionary`,
    and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
    or :class:`zope.dublincore.interfaces.IDCTimes`.

    :return: A number if it can be found, or the value of ``default``
    """
    # The _write_into argument is for the benefit of
    # to_standard_external_dictionary
    holder = _write_into if _write_into is not None else dict()

    choose_field(holder, context, StandardExternalFields_LAST_MODIFIED,
                 fields=(StandardInternalFields_LAST_MODIFIED,
                         StandardInternalFields_LAST_MODIFIEDU),
                 sup_iface=IDCTimes, sup_fields=('modified',),
                 sup_converter=_datetime_to_epoch)
    return holder.get(StandardExternalFields_LAST_MODIFIED, default)


def to_standard_external_created_time(context, default=None, _write_into=None):
    """
    Find and return a number representing the time since the epoch
    in fractional seconds at which the ``context`` was created.
    This is the same value that is used by :func:`to_standard_external_dictionary`,
    and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
    or :class:`zope.dublincore.interfaces.IDCTimes`.

    :return: A number if it can be found, or the value of ``default``
    """
    # The _write_into argument is for the benefit of
    # to_standard_external_dictionary
    holder = _write_into if _write_into is not None else dict()

    choose_field(holder, context, StandardExternalFields_CREATED_TIME,
                 fields=(StandardInternalFields_CREATED_TIME,),
                 sup_iface=IDCTimes, sup_fields=('created',),
                 sup_converter=_datetime_to_epoch)

    return holder.get(StandardExternalFields_CREATED_TIME, default)


_ext_class_ignored_modules = frozenset(('nti.externalization',
                                        'nti.externalization.datastructures',
                                        'nti.externalization.persistence',
                                        'nti.externalization.interfaces'))

def _ext_class_if_needed(self, result):
    if StandardExternalFields_CLASS not in result:
        cls = getattr(self, '__external_class_name__', None)
        if cls:
            result[StandardExternalFields_CLASS] = cls
        elif (not self.__class__.__name__.startswith('_')
              and self.__class__.__module__ not in _ext_class_ignored_modules):
            result[StandardExternalFields_CLASS] = self.__class__.__name__



def _should_never_convert(x):
    raise AssertionError("We should not be converting")

def to_standard_external_dictionary(
        self,
        mergeFrom=None,
        registry=component,
        decorate=True,
        request=_NotGiven,
        decorate_callback=_NotGiven,
        # These are ignored, present for BWC
        name=_NotGiven,
        useCache=_NotGiven,
):

    """
    Returns a dictionary representing the standard externalization of
    the object. This impl takes care of the standard attributes
    including OID (from :attr:`~persistent.interfaces.IPersistent._p_oid`) and ID (from ``self.id`` if defined)
    and Creator (from ``self.creator``).

    If the object has any
    :class:`~nti.externalization.interfaces.IExternalMappingDecorator`
    subscribers registered for it, they will be called to decorate the
    result of this method before it returns ( *unless* `decorate` is set to
    False; only do this if you know what you are doing! )

    :param dict mergeFrom: For convenience, if ``mergeFrom`` is not None, then those values will
        be added to the dictionary created by this method. The keys and
        values in ``mergeFrom`` should already be external.
    """
    result = to_minimal_standard_external_dictionary(self, mergeFrom)

    set_external_identifiers(self, result)

    choose_field(result, self, StandardExternalFields_CREATOR,
                 fields=(StandardInternalFields_CREATOR,
                         StandardExternalFields_CREATOR),
                 converter=_should_never_convert)

    to_standard_external_last_modified_time(self, _write_into=result)
    to_standard_external_created_time(self, _write_into=result)

    containerId = choose_field(result, self, StandardExternalFields_CONTAINER_ID,
                               fields=(StandardInternalFields_CONTAINER_ID,))
    if containerId:  # alias per mobile client request 20150625
        result[StandardInternalFields_CONTAINER_ID] = containerId

    if decorate:
        if request is _NotGiven:
            request = get_current_request()

        decorate_external_mapping(self, result, registry=registry,
                                  request=request)
    elif callable(decorate_callback):
        decorate_callback(self, result)

    return result


def decorate_external_mapping(self, result, registry=component, request=_NotGiven):
    for decorator in registry.subscribers((self,), IExternalMappingDecorator):
        decorator.decorateExternalMapping(self, result)

    if request is _NotGiven:
        request = get_current_request()

    if request is not None:
        for decorator in registry.subscribers((self, request), IExternalMappingDecorator):
            decorator.decorateExternalMapping(self, result)

    return result

#: This is a deprecated alias
def toExternalDictionary(*args, **kwargs): # pragma: no cover
    warnings.warn("Use to_standard_external_dictionary", FutureWarning)
    return to_standard_external_dictionary(*args, **kwargs)



def to_minimal_standard_external_dictionary(self, mergeFrom=None):
    """
    Does no decoration. Useful for non-'object' types. `self` should have a `mime_type` field.
    """

    result = LocatedExternalDict()
    if mergeFrom:
        result.update(mergeFrom)
    _ext_class_if_needed(self, result)

    mime_type = getattr(self, 'mimeType', None) or getattr(self, 'mime_type', None)
    if mime_type:
        result[StandardExternalFields_MIMETYPE] = mime_type
    return result


def is_nonstr_iter(v):
    return hasattr(v, '__iter__')


def removed_unserializable(ext):
    # XXX: Why is this here? We don't use it anymore.
    # Can it be removed?
    def _is_sequence(m):
        return not isinstance(m, collections.Mapping) and is_nonstr_iter(m)

    def _clean(m):
        if isinstance(m, collections.Mapping):
            for k, v in list(m.items()):
                if _is_sequence(v):
                    if not isinstance(v, list):
                        m[k] = list(v)
                elif not isinstance(v, collections.Mapping):
                    if not isinstance(v, _primitives):
                        m[k] = None
            values = m.values()
        elif isinstance(m, list):
            for idx, v in enumerate(m):
                if _is_sequence(v):
                    if not isinstance(v, list):
                        m[idx] = list(v)
                elif not isinstance(v, collections.Mapping):
                    if not isinstance(v, _primitives):
                        m[idx] = None
            values = m
        else:
            values = ()
        for x in values:
            _clean(x)
    if _is_sequence(ext) and not isinstance(ext, list):
        ext = list(ext)
    _clean(ext)
    return ext


#: Constant requesting JSON format data
EXT_FORMAT_JSON = 'json'


from nti.externalization._compat import import_c_accel
import_c_accel(globals(), 'nti.externalization._externalization')

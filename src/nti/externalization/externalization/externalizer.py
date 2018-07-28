# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
The driver function for the externalization process.


"""

# Our request hook function always returns None, and pylint
# flags that as useless (good for it)
# pylint:disable=assignment-from-none

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import warnings
try:
    from collections.abc import Set
except ImportError:
    from collections import Set
    from collections import Mapping
else: # pragma: no cover
    from collections.abc import Mapping
from collections import defaultdict
from weakref import WeakKeyDictionary

import BTrees.OOBTree
import persistent

from zope import component
from zope.interface.common.sequence import IFiniteSequence

from nti.externalization._base_interfaces import NotGiven
from nti.externalization._base_interfaces import PRIMITIVES
from nti.externalization._threadlocal import ThreadLocalManager
from nti.externalization.extension_points import get_current_request

from nti.externalization.interfaces import IInternalObjectExternalizer
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import ILocatedExternalSequence
from nti.externalization.interfaces import INonExternalizableReplacementFactory

from nti.externalization.externalization.replacers import DefaultNonExternalizableReplacer

from nti.externalization.externalization.dictionary import internal_to_standard_external_dictionary

from nti.externalization.externalization.decorate import decorate_external_object

logger = __import__('logging').getLogger(__name__)


# It turns out that the name we use for externalization (and really the registry, too)
# we must keep thread-local. We call into objects without any context,
# and they call back into us, and otherwise we would lose
# the name that was established at the top level.

# Stores tuples (name, memos)
_manager = ThreadLocalManager(default=lambda: (NotGiven, None))
_manager_get = _manager.get
_manager_pop = _manager.pop
_manager_push = _manager.push


#: The types that we will treat as sequences for externalization purposes. These
#: all map onto lists. (TODO: Should we just try to iter() it, ignoring strings?)
#: In addition, we also support :class:`~zope.interface.common.sequence.IFiniteSequence`
#: by iterating it and mapping onto a list. This allows :class:`~z3c.batching.interfaces.IBatch`
#: to be directly externalized.
SEQUENCE_TYPES = (
    persistent.list.PersistentList,
    Set,
    list,
    tuple,
)

#: The types that we will treat as mappings for externalization purposes. These
#: all map onto a dict.
MAPPING_TYPES = (
    persistent.mapping.PersistentMapping,
    BTrees.OOBTree.OOBTree,
    Mapping
)



class _ExternalizationState(object):

    __slots__ = (
        'name',
        'memo',
        'registry',
        'catch_components',
        'catch_component_action',
        'request',
        'default_non_externalizable_replacer',
        'decorate',
        'useCache',
        'decorate_callback',
        '_kwargs',
    )

    def __init__(self, memos,
                 name, registry, catch_components, catch_component_action,
                 request,
                 default_non_externalizable_replacer,
                 decorate=True,
                 useCache=True,
                 decorate_callback=None):
        self.name = name
        # We take a similar approach to pickle.Pickler
        # for memoizing objects we've seen:
        # we map the id of an object to a two tuple: (obj, external-value)
        # the original object is kept in the tuple to keep transient objects alive
        # and thus ensure no overlapping ids
        self.memo = memos[self.name]

        self.registry = registry
        self.catch_components = catch_components
        self.catch_component_action = catch_component_action
        self.request = request
        self.default_non_externalizable_replacer = default_non_externalizable_replacer

        self.decorate = decorate
        self.useCache = useCache
        self.decorate_callback = decorate_callback

        self._kwargs = None

    def as_kwargs(self):
        if self._kwargs is None:
            self._kwargs = dict(
                request=self.request, name=self.name,
                decorate=self.decorate, useCache=self.useCache,
                decorate_callback=self.decorate_callback
            )
        return self._kwargs

class _RecursiveCallState(dict):
    pass


_marker = object()

def _externalize_mapping(obj, state):
    # XXX: This winds up calling decorate_callback at least twice.
    result = internal_to_standard_external_dictionary(
        obj,
        None,
        state.registry,
        state.decorate,
        state.request,
        state.decorate_callback)
    if obj.__class__ is dict:
        result.pop('Class', None)
    # Note that we recurse on the original items, not the things newly added.
    # NOTE: This means that Links added here will not be externalized. There
    # is an IExternalObjectDecorator that does that
    for key, value in obj.items():
        if not isinstance(value, PRIMITIVES):
            value = _to_external_object_state(value, state,
                                              top_level=False)
        result[key] = value

    return result


def _externalize_sequence(obj, state):
    result = []
    for value in obj:
        if not isinstance(value, PRIMITIVES):
            value = _to_external_object_state(value, state,
                                              top_level=False)
        result.append(value)
    result = state.registry.getAdapter(result,
                                       ILocatedExternalSequence)
    return result


_usable_externalObject_cache = WeakKeyDictionary()
_usable_externalObject_cache_get = _usable_externalObject_cache.get

try:
    # pylint:disable=ungrouped-imports
    from zope.testing import cleanup
except ImportError: # pragma: no cover
    pass
else:
    cleanup.addCleanUp(_usable_externalObject_cache.clear)


def _obj_has_usable_externalObject(obj):
    # This is for legacy code support, to allow existing methods to
    # move to adapters and call us without infinite recursion.
    # We use __class__ instead of type() to allow for proxies;
    # The proxy itself cannot implement toExternalObject
    kind = obj.__class__
    answer = _usable_externalObject_cache_get(kind)
    if answer is None:
        answer = False
        has_ext_obj = hasattr(kind, 'toExternalObject')
        if has_ext_obj:
            ext_ignored = getattr(kind, '__ext_ignore_toExternalObject__', None)
            answer = not ext_ignored
            if ext_ignored is not None: # pragma: no cover
                warnings.warn("The type %r still has __ext_ignore_toExternalObject__. "
                              "Remove it and toExternalObject()." % (kind,),
                              FutureWarning)

        _usable_externalObject_cache[kind] = answer

    return answer


def _externalize_object(obj, state):
    # Unlike the other functions, this one returns None to indicate
    # that it failed and legacy behaviour is needed.

    # TODO: This is needless for the mapping types and sequence types. rework to avoid.
    # Benchmarks show that simply moving it into the last block doesn't actually save much
    # (due to all the type checks in front of it?)
    result = toExternalObject = None

    obj_has_usable_external_object = _obj_has_usable_externalObject(obj)
    if obj_has_usable_external_object:
        toExternalObject = obj.toExternalObject
    else:
        adapter = state.registry.queryAdapter(obj, IInternalObjectExternalizer, state.name)

        if adapter is None and state.name != '':
            # try for the default, but allow passing name of None to
            # disable (?)
            adapter = state.registry.queryAdapter(obj, IInternalObjectExternalizer)

        if adapter is not None:
            toExternalObject = adapter.toExternalObject

    if toExternalObject is not None:
        result = toExternalObject(**state.as_kwargs())

    return result


def _to_external_object_state(obj, state, top_level=False):
    # This function is way to long and ugly. Given cython's 0 function call overhead,
    # we can probably refactor.
    # pylint:disable=too-many-branches
    __traceback_info__ = obj

    assert obj is not None # caught by primitives already.

    orig_obj_id = id(obj) # XXX: Relatively expensive on PyPy
    if state.useCache:
        value = state.memo.get(orig_obj_id, None)
        result = value[1] if value is not None else None
        if result is None:  # mark as in progress
            state.memo[orig_obj_id] = (obj, _marker)
        elif result is not _marker:
            return result
        else:
            logger.warning("Recursive call to object %s.", obj)
            result = internal_to_standard_external_dictionary(obj,
                                                              decorate=False)

            return _RecursiveCallState(result)

    try:
        # TODO: This is needless for the mapping types and sequence types. rework to avoid.
        # Benchmarks show that simply moving it into the last block doesn't actually save much
        # (due to all the type checks in front of it?)

        result = _externalize_object(obj, state)
        if result is None:
            # Legacy codepaths

            if hasattr(obj, "toExternalDictionary"):
                result = obj.toExternalDictionary(**state.as_kwargs())
            elif hasattr(obj, "toExternalList"):
                result = obj.toExternalList()
            elif isinstance(obj, MAPPING_TYPES):
                result = _externalize_mapping(obj, state)
            elif isinstance(obj, SEQUENCE_TYPES) or IFiniteSequence.providedBy(obj):
                result = _externalize_sequence(obj, state)
            else:
                # Otherwise, we probably won't be able to JSON-ify it.
                # TODO: Should this live here, or at a higher level where the ultimate
                # external target/use-case is known?
                replacer = state.default_non_externalizable_replacer
                result = state.registry.queryAdapter(obj, INonExternalizableReplacementFactory,
                                                     default=replacer)(obj)

        decorate_external_object(
            state.decorate, state.decorate_callback,
            IExternalObjectDecorator, 'decorateExternalObject',
            obj, result,
            state.registry, state.request
        )

        if state.useCache:  # save result
            state.memo[orig_obj_id] = (obj, result)
        return result
    except state.catch_components as t:
        if top_level or state.catch_component_action is None:
            raise
        # python rocks. catch_components could be an empty tuple, meaning we catch nothing.
        # or it could be any arbitrary list of exceptions.
        # NOTE: we cannot try to to-string the object, it may try to call back to us
        # NOTE2: In case we encounter a proxy (zope.container.contained.ContainedProxy)
        # the type(o) is not reliable. Only the __class__ is.
        logger.exception("Exception externalizing component object %s/%s",
                         type(obj), obj.__class__)
        return state.catch_component_action(obj, t)



def to_external_object(
        obj,
        name=NotGiven,
        registry=component,
        catch_components=(),
        catch_component_action=None,
        request=NotGiven,
        decorate=True,
        useCache=True,
        # XXX: Why do we have this? It's only used when decorate is False,
        # which doesn't make much sense.
        decorate_callback=NotGiven,
        default_non_externalizable_replacer=DefaultNonExternalizableReplacer
):
    """
    Translates the object into a form suitable for external
    distribution, through some data formatting process. See
    :const:`SEQUENCE_TYPES` and :const:`MAPPING_TYPES` for details on
    what we can handle by default.

    :param string name: The name of the adapter to
        :class:`~nti.externalization.interfaces.IInternalObjectExternalizer`
        to look for. Defaults to the empty string (the default
        adapter). If you provide a name, and an adapter is not found,
        we will still look for the default name (unless the name you
        supply is None).
    :param tuple catch_components: A tuple of exception classes to
        catch when externalizing sub-objects (e.g., items in a list or
        dictionary). If one of these exceptions is caught, then
        *catch_component_action* will be called to raise or replace
        the value. The default is to catch nothing.
    :param callable catch_component_action: If given with
        *catch_components*, a function of two arguments, the object
        being externalized and the exception raised. May return a
        different object (already externalized) or re-raise the
        exception. There is no default, but
        :func:`catch_replace_action` is a good choice.
    :param callable default_non_externalizable_replacer: If we are
        asked to externalize an object and cannot, and there is no
        :class:`~nti.externalization.interfaces.INonExternalizableReplacer`
        registered for it, then call this object and use the results.
    :param request: If given, the request that the object is being
        externalized on behalf of. If given, then the object
        decorators will also look for subscribers to the object plus
        the request (like traversal adapters); this is a good way to
        separate out request or user specific code.
    :param decorate_callback: Callable to be invoked in case there is
        no decaration
    """

    # Catch the primitives up here, quickly. This catches
    # numbers, strings, and None
    if isinstance(obj, PRIMITIVES):
        return obj

    manager_top = _manager_get() # (name, memos)
    if name is NotGiven:
        name = manager_top[0]
    if name is NotGiven:
        name = ''
    if request is NotGiven:
        request = get_current_request()

    memos = manager_top[1]
    if memos is None:
        # Don't live beyond this dynamic function call
        memos = defaultdict(dict)

    state = _ExternalizationState(memos, name, registry, catch_components, catch_component_action,
                                  request,
                                  default_non_externalizable_replacer,
                                  decorate, useCache, decorate_callback)

    _manager_push((name, memos))

    try:
        return _to_external_object_state(obj, state, top_level=True)
    finally:
        _manager_pop()


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.externalization._externalizer')

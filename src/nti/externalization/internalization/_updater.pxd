# definitions for internalization.py
import cython

from ._externals cimport resolve_externals
from ._events cimport _notifyModified
from ._factories cimport find_factory_for


# imports
cdef NotGiven
cdef component
cdef MutableSequence
cdef MutableMapping
cdef inspect
cdef numbers
cdef warnings
cdef string_types
cdef iteritems
cdef component
cdef interface
cdef IInternalObjectUpdater
cdef IInternalObjectIO
cdef INamedExternalizedObjectFactoryFinder

# optimizations

cdef IPersistent_providedBy


# constants
cdef tuple PRIMITIVES
cdef dict _EMPTY_DICT


@cython.internal
@cython.final
@cython.freelist(1000)
cdef class _RecallArgs(object):
    cdef context
    cdef pre_hook
    cdef bint require_updater
    cdef bint notify

@cython.internal
@cython.final
cdef class DefaultInternalObjectFactoryFinder(object):
    pass

cdef DefaultInternalObjectFactoryFinder _default_factory_finder


cdef inline _invoke_factory(factory, value)

cdef _invoke_updater(containedObject, externalObject, updater,
                     list external_keys, _RecallArgs args)
cdef _update_sequence(externalObject, _RecallArgs args,
                      destination_name=*,
                      find_factory_for_named_value=*)
cpdef _find_INamedExternalizedObjectFactoryFinder(containedObject)
cdef _update_from_external_object(containedObject, externalObject, _RecallArgs args)

cpdef update_from_external_object(containedObject,
                                  externalObject,
                                  registry=*,
                                  context=*,
                                  bint require_updater=*,
                                  bint notify=*,
                                  pre_hook=*)

cdef dict _argspec_cacheg
cdef str _UPDATE_ARGS_TWO
cdef str _UPDATE_ARGS_ONE
cdef str _UPDATE_ARGS_CONTEXT_KW
cdef inline _get_update_signature(updater)

cdef dict _upsable_updateFromExternalObject_cache
cdef _obj_has_usable_updateFromExternalObject(obj)

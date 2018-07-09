# definitions for internalization.py
import cython

from ._externals cimport resolve_externals
from ._events cimport _notifyModified
from ._factories cimport find_factory_for

# imports
cdef MutableSequence
cdef MutableMapping
cdef inspect
cdef numbers
cdef warnings
cdef string_types
cdef iteritems
cdef component
cdef IInternalObjectUpdater

# optimizations

cdef IPersistent_providedBy

# constants
cdef tuple PRIMITIVES
cdef dict _EMPTY_DICT


@cython.internal
@cython.final
@cython.freelist(1000)
cdef class _RecallArgs(object):
    cdef registry
    cdef context
    cdef pre_hook
    cdef bint require_updater
    cdef bint notify


cdef _recall(k, obj, ext_obj, _RecallArgs kwargs)

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
cdef _get_update_signature(updater)

cdef dict _upsable_updateFromExternalObject_cache
cdef _obj_has_usable_updateFromExternalObject(obj)

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
    cdef require_updater
    cdef notify
    cdef pre_hook


cdef _recall(k, obj, ext_obj, _RecallArgs kwargs)

cpdef update_from_external_object(containedObject,
                                  externalObject,
                                  registry=*,
                                  context=*,
                                  require_updater=*,
                                  notify=*,
                                  pre_hook=*)

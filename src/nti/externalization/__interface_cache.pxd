import cython

cdef cache_instances

@cython.final
@cython.internal
@cython.freelist(1000)
cdef class InterfaceCache(object):
    cdef __weakref__
    cdef iface
    cdef frozenset ext_all_possible_keys
    cdef ext_accept_external_id
    cdef frozenset ext_primitive_out_ivars
    cdef dict modified_event_attributes

@cython.locals(x=InterfaceCache)
cdef _cache_cleanUp(instances)

cpdef InterfaceCache cache_for(externalizer, ext_self)
cpdef InterfaceCache cache_for_key(key, ext_self)

# declarations for _base_interfaces.py

import cython

@cython.final
@cython.internal
cdef class _NotGiven(object):
    pass


cdef class LocatedExternalDict(dict):
    cdef public __name__
    cdef public __parent__
    cdef public __acl__
    cdef readonly mimeType

# definitions for internalization.py
import cython


# imports
cdef MutableSequenc
cdef component
cdef IExternalReferenceResolver

# XXX: This is only public for testing
cpdef resolve_externals(object_io, updating_object, externalObject,
                        context=*)

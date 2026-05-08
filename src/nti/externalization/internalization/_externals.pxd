# definitions for internalization.py
import cython


# imports
cdef IExternalReferenceResolver
cdef MutableSequence
cdef component

# XXX: This is only public for testing
cpdef resolve_externals(object_io, updating_object, externalObject,
                        context=*)

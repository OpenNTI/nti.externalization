# definitions for internalization.py
import cython



# imports
cdef sys

cdef text_type
cdef reraise

cdef implementedBy

cdef IField
cdef IFromUnicode
cdef SchemaNotProvided
cdef ValidationError
cdef WrongContainedType
cdef WrongType

# optimizations
cdef IField_providedBy


cdef noop()


@cython.final
@cython.internal
@cython.freelist(1000)
cdef class SetattrSet(object):
    cdef ext_self
    cdef str field_name
    cdef value

@cython.final
@cython.internal
@cython.freelist(1078)
cdef class FieldSet(object):
    cdef ext_self
    cdef field
    cdef value

cpdef _adapt_sequence(field, value)
cdef bint _all_SchemaNotProvided(sequence)

cpdef validate_field_value(self, field_name, field, value)
cpdef validate_named_field_value(self, iface, field_name, value)

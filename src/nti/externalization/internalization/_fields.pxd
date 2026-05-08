# definitions for internalization.py
import cython



# imports
cdef sys

cdef text_type


cdef implementedBy

cdef IField
# Exceptions we catche
cdef SchemaNotProvided
cdef SchemaNotCorrectlyImplemented
cdef ValidationError
cdef WrongContainedType
cdef WrongType

cdef FieldProperty
cdef NO_VALUE
cdef FieldUpdatedEvent

cdef notify

# optimizations
cdef IField_providedBy
cdef get_exc_info


cpdef noop()
cpdef _FieldProperty__set__valid(self, inst, value)
cdef _FieldProperty_orig_set


@cython.final
@cython.internal
@cython.freelist(1000)
cdef class SetattrSet(object):
    cdef ext_self
    cdef str field_name # setattr() wants native strings
    cdef value

@cython.final
@cython.internal
@cython.freelist(1078)
cdef class FieldSet(object):
    cdef ext_self
    cdef field
    cdef value

cpdef _adapt_sequence(field, value)
cdef bint _all_SchemaNotProvided(sequence) except *

cdef _handle_SchemaNotProvided(field_name, field, value)
cdef _handle_WrongType(field_name, field, value)
cdef _handle_WrongContainedType(field_name, field, value)

cdef tuple _CONVERTERS

@cython.locals(
    meth_name_kind=tuple,
)
cpdef validate_field_value(self, str field_name, field, value)
cpdef validate_named_field_value(self, iface, str field_name, value)

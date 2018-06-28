# definitions for internalization.py
import cython

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport get_standard_internal_fields
from nti.externalization.__base_interfaces cimport StandardInternalFields as SIF

cdef SEF StandardExternalFields
cdef SIF StandardInternalFields


# imports
cdef IField
cdef IFromUnicode
cdef sys
cdef SchemaNotProvided
cdef ValidationError
cdef reraise
cdef WrongType

cdef warnings
cdef collections
cdef component
cdef iteritems
cdef IInternalObjectUpdater
cdef inspect
cdef Attributes
cdef ObjectModifiedFromExternalEvent
cdef _zope_event_notify
cdef text_type
cdef IFromUnicode

# optimizations

cdef IPersistent_providedBy
cdef interface_implementedBy

# constants
cdef tuple _primitives

cdef _noop()

@cython.final
@cython.internal
@cython.freelist(1000)
cdef class _FirstSet(object):
    cdef ext_self
    cdef str field_name
    cdef value

@cython.final
@cython.internal
@cython.freelist(1078)
cdef class _FieldSet(object):
    cdef ext_self
    cdef field
    cdef value

@cython.locals(
    l=list
)
cdef _notifyModified(containedObject, externalObject, updater=*, external_keys=*,
                     eventFactory=*, dict kwargs=*)

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
# XXX: This is only public for testing
cpdef _resolve_externals(object_io, updating_object, externalObject,
                         registry=*, context=*)


cpdef find_factory_for(externalized_object, registry=*)

cpdef validate_field_value(self, field_name, field, value)
cpdef validate_named_field_value(self, iface, field_name, value)

cpdef update_from_external_object(containedObject,
                                  externalObject,
                                  registry=*,
                                  context=*,
                                  require_updater=*,
                                  notify=*,
                                  pre_hook=*)

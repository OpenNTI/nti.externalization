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
cdef IMimeObjectFactory
cdef IClassObjectFactory
cdef IExternalizedObjectFactoryFinder

# optimizations

cdef IPersistent_providedBy
cdef interface_implementedBy
cdef component_queryUtility
cdef component_queryAdapter

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


cdef _notifyModified(containedObject, externalObject, updater=*, external_keys=*,
                     eventFactory=*, dict kwargs=*)

@cython.final
@cython.internal
cdef class _DefaultExternalizedObjectFactoryFinder(object):

    cpdef find_factory(self, externalized_object)

cdef _search_for_external_factory(class_name)
cpdef find_factory_for_class_name(class_name)
cdef _find_factory_for_mime_or_class(externalized_object)

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

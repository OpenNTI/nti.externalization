# Definitions for datastructures.py
import cython


from nti.externalization.externalization._externalizer cimport to_external_object as _toExternalObject

from nti.externalization.externalization._dictionary cimport to_minimal_standard_external_dictionary
from nti.externalization.externalization._dictionary cimport internal_to_standard_external_dictionary

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport get_standard_internal_fields
from nti.externalization.__base_interfaces cimport StandardInternalFields as SIF

from nti.externalization.internalization._fields cimport validate_named_field_value

from nti.externalization.__interface_cache cimport cache_for

cdef IInternalObjectIO
cdef SEF StandardExternalFields
cdef SIF StandardInternalFields
cdef validate_named_field_value
cdef make_repr
cdef isSyntheticKey
cdef find_most_derived_interface
cdef NotGiven

cdef class ExternalizableDictionaryMixin(object):
    # This is a mixin used with other C base classes (E.g., persistent)
    # in this package. That's not a great idea, but it exists.
    # So this cannot have any C-level attributes or vtable (cdef or
    # cpdef ivars/methods) without causing metaclass problems.
    pass

cdef class AbstractDynamicObjectIO(ExternalizableDictionaryMixin):

    cpdef _ext_all_possible_keys(self)
    cpdef _ext_setattr(self, ext_self, k, value)
    cpdef _ext_getattr(self, ext_self, k)

    @cython.locals(
        k=str # cython can optimize k.startswith('constantstring')
    )
    cpdef _ext_keys(self)
    cpdef _ext_primitive_keys(self)
    cpdef _ext_accept_update_key(self, k, ext_self, ext_keys)
    cpdef _ext_accept_external_id(self, ext_self, parsed)


cdef class ExternalizableInstanceDict(AbstractDynamicObjectIO):
    pass

cdef class InterfaceObjectIO(AbstractDynamicObjectIO):
    cdef _ext_self
    cdef readonly _iface
    cdef readonly bint validate_after_update
    # The dict is necessary because we assign to _ext_primitive_out_ivars,
    # which so far was only defined as a class attribute (for
    # which we use generic getattr)
    cdef dict __dict__
    #cdef _ext_primitive_out_ivars

    cpdef _ext_find_schema(self, ext_self, iface_upper_bound)
    cpdef _ext_find_primitive_keys(self)
    cpdef _ext_schemas_to_consider(self, ext_self)
    cpdef _validate_after_update(self, iface, ext_self)


cdef class ModuleScopedInterfaceObjectIO(InterfaceObjectIO):

    @cython.locals(
        search_module_name=str,
    )
    cpdef _ext_schemas_to_consider(self, ext_self)


cdef tuple _primitives

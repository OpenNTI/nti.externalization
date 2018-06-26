# Definitions for datastructures.py
import cython


from nti.externalization._externalization cimport toExternalObject as _toExternalObject
from nti.externalization._externalization cimport stripSyntheticKeysFromExternalDictionary
from nti.externalization._externalization cimport _isMagicKey
from nti.externalization._externalization cimport to_minimal_standard_external_dictionary
from nti.externalization._externalization cimport to_standard_external_dictionary



cdef IInternalObjectIO
cdef StandardExternalFields
cdef StandardInternalFields
cdef validate_named_field_value
cdef make_repr
cdef isSyntheticKey
cdef find_most_derived_interface

cdef class ExternalizableDictionaryMixin(object):
    pass

cdef class AbstractDynamicObjectIO(ExternalizableDictionaryMixin):
    pass

cdef class ExternalizableInstanceDict(AbstractDynamicObjectIO):
    pass

cdef class InterfaceObjectIO(AbstractDynamicObjectIO):
    cdef _ext_self
    cdef readonly _iface
    cdef readonly bint validate_after_update
    cdef dict __dict__
    #cdef _ext_primitive_out_ivars
    pass

cdef class ModuleScopedInterfaceObjectIO(InterfaceObjectIO):
    pass

@cython.final
@cython.internal
@cython.freelist(1000)
cdef class _InterfaceCache(object):
    cdef __weakref__
    cdef iface
    cdef ext_all_possible_keys
    cdef ext_accept_external_id
    cdef set ext_primitive_out_ivars


cdef _InterfaceCache _cache_for(externalizer, ext_self)
@cython.locals(x=_InterfaceCache)
cdef _cache_cleanUp()

cdef tuple _primitives

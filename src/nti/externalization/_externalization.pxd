# definitions for externalization.pxd
import cython

from .__base_interfaces cimport make_external_dict

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport get_standard_internal_fields
from nti.externalization.__base_interfaces cimport StandardInternalFields as SIF


cdef SEF StandardExternalFields
cdef SIF StandardInternalFields


# Imports
cdef numbers
cdef warnings
cdef collections
cdef component
cdef interface
cdef defaultdict

cdef IDCTimes
cdef IFiniteSequence
cdef IPrincipal
cdef system_user

cdef identity
cdef ThreadLocalManager
cdef get_current_request
cdef set_external_identifiers
cdef IExternalMappingDecorator
cdef IExternalObject
cdef IExternalObjectDecorator
cdef ILocatedExternalSequence
cdef INonExternalizableReplacement
cdef INonExternalizableReplacer
cdef StandardExternalFields
cdef StandardInternalFields
cdef NotGiven


# Constants


cdef _manager, _manager_get, _manager_pop, _manager_push
cdef tuple _primitives
cdef _marker

cdef tuple SEQUENCE_TYPES
cdef tuple MAPPING_TYPES

# _NonExternalizableObject is decorated, can't be cdef class
# or even declared
# cdef _NonExternalizableObject

cpdef DefaultNonExternalizableReplacer(obj)

cdef bint is_system_user(obj)


@cython.final
@cython.internal
@cython.freelist(1000)
cdef class _ExternalizationState(object):
    cdef dict memo

    cdef basestring name
    cdef registry
    cdef catch_components
    cdef catch_component_action
    cdef request
    cdef default_non_externalizable_replacer


# can't use freelist on subclass
@cython.final
@cython.internal
cdef class _RecursiveCallState(dict):
    pass


#@cython.locals(
#)
cpdef toExternalObject(obj,
                       name=*,
                       registry=*,
                       catch_components=*,
                       catch_component_action=*,
                       request=*,
                       bint decorate=*,
                       bint useCache=*,
                       decorate_callback=*,
                       default_non_externalizable_replacer=*)

@cython.locals(
    obj_has_usable_external_object=bint,
)
cdef _to_external_object_state(obj, _ExternalizationState state,
                               bint top_level=*,
                               bint decorate=*,
                               bint useCache=*,
                               decorate_callback=*)

cpdef stripSyntheticKeysFromExternalDictionary(external)

cdef frozenset _SYNTHETIC_KEYS
cdef frozenset _syntheticKeys()
cpdef bint _isMagicKey(str key)
#cpdef bint isSyntheticKey(str key)

cpdef choose_field(result, self,
                   unicode ext_name,
                   converter=*,
                   tuple fields=*,
                   sup_iface=*,
                   sup_fields=*,
                   sup_converter=*)

cpdef to_standard_external_last_modified_time(context, default=*, _write_into=*)
cpdef to_standard_external_created_time(context, default=*, _write_into=*)

cdef frozenset _ext_class_ignored_modules


cdef void _ext_class_if_needed(self, result) except *

cdef tuple _CREATOR_FIELDS
cdef void _fill_creator(result, self) except *

cdef tuple _CONTAINER_FIELDS
cdef void _fill_container(result, self) except *

cpdef void _should_never_convert(x) except *


cpdef internal_to_standard_external_dictionary(self,
                                               mergeFrom=*,
                                               registry=*,
                                               bint decorate=*,
                                               request=*,
                                               decorate_callback=*)


cpdef decorate_external_mapping(self, result, registry=*, request=*)


cpdef to_minimal_standard_external_dictionary(self, mergeFrom=*)

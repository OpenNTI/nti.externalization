# definitions for externalization.pxd
import cython

# Imports
cdef numbers
cdef warnings
cdef collections
cdef component
cdef interface

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
cdef LocatedExternalDict
cdef StandardExternalFields
cdef StandardInternalFields

# Constants
# Despite the name, NotGiven is
# used from representation.py
# TODO: cython compile representation.py and then make this
# a cdef
#cpdef _NotGiven
cdef _manager
cdef tuple _primitives
cdef _marker

cdef tuple SEQUENCE_TYPES
cdef tuple MAPPING_TYPES

# _NonExternalizableObject is decorated, can't be cdef class
# or even declared
# cdef _NonExternalizableObject

cpdef DefaultNonExternalizableReplacer(obj)

@cython.final
@cython.internal
@cython.freelist(1000)
cdef class _ExternalizationState(object):
    cdef dict __dict__

# can't use freelist on subclass
@cython.final
@cython.internal
cdef class _RecursiveCallState(dict):
    pass


cpdef toExternalObject(obj,
                       name=*,
                       registry=*,
                       catch_components=*,
                       catch_component_action=*,
                       request=*,
                       decorate=*,
                       useCache=*,
                       decorate_callback=*,
                       default_non_externalizable_replacer=*)


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

cpdef choose_field(result, self, ext_name,
                   converter=*,
                   tuple fields=*,
                   sup_iface=*,
                   sup_fields=*,
                   sup_converter=*)

cpdef to_standard_external_last_modified_time(context, default=*, _write_into=*)
cpdef to_standard_external_created_time(context, default=*, _write_into=*)

cdef frozenset _ext_class_ignored_modules

cdef void _ext_class_if_needed(self, result) except *

# TODO: If we bring LocatedExternalDict into cython, we could typo
# some args and results below and in choose_field and to_standard_external_*. Does that have any
# improvement?
cpdef to_standard_external_dictionary(self, mergeFrom=*,
                                      registry=*,
                                      decorate=*,
                                      request=*,
                                      decorate_callback=*,
                                      name=*,
                                      useCache=*)


cpdef decorate_external_mapping(self, result, registry=*, request=*)


cpdef to_minimal_standard_external_dictionary(self, mergeFrom=*)

# definitions for externalization.pxd
import cython

from nti.externalization.externalization._dictionary cimport internal_to_standard_external_dictionary
from nti.externalization.__base_interfaces cimport LocatedExternalDict as LED
from nti.externalization.externalization._decorate cimport decorate_external_object

# Imports
cdef defaultdict
cdef six
cdef numbers


cdef queryAdapter
cdef getAdapter
cdef IFiniteSequence

cdef ThreadLocalManager
cdef get_current_request
cdef set_external_identifiers
cdef IExternalMappingDecorator
cdef IExternalObject
cdef IExternalObjectDecorator
cdef ILocatedExternalSequence
cdef INonExternalizableReplacement
cdef INonExternalizableReplacer
cdef DefaultNonExternalizableReplacer
cdef NotGiven
cdef IInternalObjectExternalizer


# Constants
cdef logger

cdef _manager, _manager_get, _manager_pop, _manager_push
cpdef tuple PRIMITIVES
cdef _marker

cdef tuple SEQUENCE_TYPES
cdef tuple MAPPING_TYPES


@cython.final
@cython.internal
@cython.freelist(1000)
cdef class _ExternalizationState(object):
    cdef dict memo

    cdef basestring name
    cdef catch_components
    cdef catch_component_action
    cdef request
    cdef default_non_externalizable_replacer

    cdef bint decorate
    cdef bint useCache
    cdef decorate_callback

    cdef dict _kwargs

    cdef dict as_kwargs(self)

# can't use freelist on subclass
@cython.final
@cython.internal
cdef class _RecursiveCallState(dict):
    pass


#@cython.locals(
#)
cpdef to_external_object(
    obj,
    name=*,
    registry=*,
    catch_components=*,
    catch_component_action=*,
    request=*,
    bint decorate=*,
    bint useCache=*,
    decorate_callback=*,
    default_non_externalizable_replacer=*
)

cdef LED _externalize_mapping(obj, _ExternalizationState state)

cdef _externalize_sequence(obj, _ExternalizationState state)

cdef _usable_externalObject_cache
cdef _usable_externalObject_cache_get

@cython.locals(
    has_ext_obj=bint,
)
cpdef _obj_has_usable_externalObject(obj)

cdef _externalize_object(obj, _ExternalizationState state)

@cython.locals(
    obj_has_usable_external_object=bint,
)
cdef _to_external_object_state(obj, _ExternalizationState state,
                               bint top_level=*)

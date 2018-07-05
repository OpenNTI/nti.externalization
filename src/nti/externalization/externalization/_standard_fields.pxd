import cython

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport get_standard_internal_fields
from nti.externalization.__base_interfaces cimport StandardInternalFields as SIF

from nti.externalization.externalization._fields cimport choose_field

# Imports
cdef IDCTimes
cdef type text_type


# Constants
cdef SEF StandardExternalFields
cdef SIF StandardInternalFields

cdef tuple _LAST_MOD_FIELDS
cdef tuple _LAST_MOD_SUP_FIELDS
cdef tuple _CREATED_TIME_FIELDS
cdef tuple _CREATED_TIME_SUP_FIELDS
cdef tuple _CREATOR_FIELDS
cdef tuple _CONTAINER_FIELDS
cdef _EXT_CLASS_IGNORED_MODULES

cdef basestring _SYSTEM_USER_NAME
cdef basestring _SYSTEM_USER_ID
cdef IPrincipal_providedBy


cpdef datetime_to_unix_time(dt)

cpdef get_last_modified_time(context, default=*, _write_into=*)
cpdef get_created_time(context, default=*, _write_into=*)

cdef _system_user_converter(obj)
cpdef get_creator(context, default=*, _write_into=*)


cpdef get_container_id(context, default=*, _write_into=*)

cpdef get_class(context, _write_into=*)

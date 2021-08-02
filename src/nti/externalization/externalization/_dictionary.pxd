# definitions for externalization.pxd
import cython

from nti.externalization.__base_interfaces cimport make_external_dict
from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport get_default_externalization_policy
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport LocatedExternalDict as LED
from nti.externalization.__base_interfaces cimport ExternalizationPolicy

from ._standard_fields cimport get_last_modified_time
from ._standard_fields cimport get_created_time
from ._standard_fields cimport get_creator
from ._standard_fields cimport get_container_id
from ._standard_fields cimport get_class

from ._decorate cimport decorate_external_object

cdef SEF StandardExternalFields
cdef ExternalizationPolicy DEFAULT_EXTERNALIZATION_POLICY


# Imports
cdef warnings
cdef component


cdef set_external_identifiers
cdef IExternalStandardDictionaryDecorator

cdef NotGiven


# Constants


cpdef LED internal_to_standard_external_dictionary(
    self,
    mergeFrom=*,
    bint decorate=*,
    request=*,
    decorate_callback=*,
    ExternalizationPolicy policy=*,
)


cpdef to_minimal_standard_external_dictionary(self, mergeFrom=*)

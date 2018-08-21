# definitions for externalization.pxd
import cython

from nti.externalization.__base_interfaces cimport make_external_dict
from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from nti.externalization.__base_interfaces cimport LocatedExternalDict as LED

from ._standard_fields cimport get_last_modified_time
from ._standard_fields cimport get_created_time
from ._standard_fields cimport get_creator
from ._standard_fields cimport get_container_id
from ._standard_fields cimport get_class

from ._decorate cimport decorate_external_object

cdef SEF StandardExternalFields


# Imports
cdef warnings
cdef component


cdef set_external_identifiers
cdef IExternalMappingDecorator

cdef NotGiven


# Constants


cpdef LED internal_to_standard_external_dictionary(self,
                                                   mergeFrom=*,
                                                   bint decorate=*,
                                                   request=*,
                                                   decorate_callback=*)


cpdef to_minimal_standard_external_dictionary(self, mergeFrom=*)

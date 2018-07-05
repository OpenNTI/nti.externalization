# definitions for externalization.pxd
import cython

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF


cdef SEF StandardExternalFields


# Imports
cdef type text_type


# Constants
cdef basestring _SYSTEM_USER_NAME
cdef basestring _SYSTEM_USER_ID
cdef identity
cdef IPrincipal_providedBy
cdef logger


cdef bint is_system_user(obj) except *

cpdef choose_field(result, self,
                   unicode ext_name,
                   converter=*,
                   tuple fields=*,
                   sup_iface=*,
                   sup_fields=*,
                   sup_converter=*)

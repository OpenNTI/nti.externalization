# definitions for externalization.pxd
import cython

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF


cdef SEF StandardExternalFields

# Imports


# Constants
cdef logger

cpdef choose_field(result, self,
                   unicode ext_name,
                   converter=*,
                   tuple fields=*,
                   sup_iface=*,
                   sup_fields=*,
                   sup_converter=*)

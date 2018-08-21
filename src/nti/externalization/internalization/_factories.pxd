# definitions for internalization.py
import cython

from nti.externalization.__base_interfaces cimport get_standard_external_fields
from nti.externalization.__base_interfaces cimport StandardExternalFields as SEF
from ._legacy_factories cimport search_for_external_factory

cdef SEF StandardExternalFields


# imports
cdef component
cdef interface
cdef NotGiven
cdef IClassObjectFactory
cdef IExternalizedObjectFactoryFinder
cdef IFactory
cdef IMimeObjectFactory

# optimizations

cdef component_queryUtility
cdef component_queryAdapter

# module contents

@cython.final
@cython.internal
cdef class _DefaultExternalizedObjectFactoryFinder(object):

    cpdef find_factory(self, externalized_object)


cdef _search_for_class_factory(externalized_object, class_name)
cdef _search_for_mime_factory(externalized_object, mime_type)
cpdef find_factory_for_class_name(class_name)
cdef _find_factory_for_mime_or_class(externalized_object)


cpdef find_factory_for(externalized_object, registry=*)

# definitions for internalization.py
import cython


# imports
cdef types
cdef warnings

cdef component
cdef resolve

cdef _ILegacySearchModuleFactory
cdef NotGiven

## module contents

# public
cpdef register_legacy_search_module(module_name)

cpdef list find_factories_in_module(module, case_sensitive=*)

# private

cdef set _ext_factory_warnings
cpdef search_for_external_factory(class_name)

cdef register_factories_from_search_set()
cdef register_factories_from_module(module)

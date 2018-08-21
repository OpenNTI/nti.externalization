cdef get_current_request
cdef NotGiven
cdef IExternalMappingDecorator
cdef subscribers

cpdef decorate_external_object(bint do_decorate, call_if_not_decorate,
                               decorate_interface, str decorate_meth_name,
                               original_object, external_object,
                               registry, request)

cpdef decorate_external_mapping(original_object, external_object, registry, request)

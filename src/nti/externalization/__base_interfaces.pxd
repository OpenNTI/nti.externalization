# declarations for _base_interfaces.py

import cython

@cython.final
@cython.internal
cdef class _NotGiven(object):
    pass

cdef dict_init
cdef dict_update

cdef class LocatedExternalDict(dict):
    cdef public __name__
    cdef public __parent__
    cdef public __acl__
    cdef public mimeType
    cdef dict __dict__

    cdef update_from_other(self, other)

cpdef LocatedExternalDict make_external_dict()

cdef class StandardExternalFields(object):

    cdef readonly str ID
    cdef readonly str OID
    cdef readonly str HREF
    cdef readonly str INTID
    cdef readonly str NTIID
    cdef readonly str CREATOR
    cdef readonly str CONTAINER_ID
    cdef readonly str CREATED_TIME
    cdef readonly str LAST_MODIFIED
    cdef readonly str CLASS
    cdef readonly str LINKS
    cdef readonly str MIMETYPE
    cdef readonly str ITEMS
    cdef readonly str TOTAL
    cdef readonly str ITEM_COUNT

    cdef readonly frozenset _ALL_ATTR_NAMES
    cdef readonly frozenset _ALL_EXTERNAL_KEYS

cdef StandardExternalFields _standard_external_fields

cpdef StandardExternalFields get_standard_external_fields()

cdef class StandardInternalFields(object):

    cdef readonly str ID
    cdef readonly str NTIID
    cdef readonly str CREATOR
    cdef readonly str CREATED_TIME
    cdef readonly str CONTAINER_ID
    cdef readonly str LAST_MODIFIED
    cdef readonly str LAST_MODIFIEDU

cdef StandardInternalFields _standard_internal_fields

cpdef StandardInternalFields get_standard_internal_fields()

@cython.final
cdef class ExternalizationPolicy(object):
    cdef readonly bint use_iso8601_for_unix_timestamp

cdef ExternalizationPolicy DEFAULT_EXTERNALIZATION_POLICY

cpdef ExternalizationPolicy get_default_externalization_policy()

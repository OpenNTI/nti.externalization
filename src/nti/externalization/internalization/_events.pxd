# definitions for internalization.py
import cython



# imports
cdef providedBy
cdef _zope_event_notify
cdef ObjectModifiedFromExternalEvent


@cython.final
@cython.internal
cdef class _Attributes(object):
    cdef public interface
    cdef public set attributes

@cython.locals(
    attrs=_Attributes,
)
cdef _make_modified_attributes(containedObject, external_keys)

cdef _make_modified_event(containedObject, externalObject, updater,
                          attributes, dict kwargs)

cpdef _notifyModified(containedObject, externalObject, updater, external_keys,
                      dict kwargs)

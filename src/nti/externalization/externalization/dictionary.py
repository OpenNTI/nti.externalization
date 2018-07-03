# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
The basics of turning objects into dictionaries.

"""

# Our request hook function always returns None, and pylint
# flags that as useless (good for it)
# pylint:disable=assignment-from-none

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import warnings


from zope import component

from nti.externalization._base_interfaces import make_external_dict
from nti.externalization._base_interfaces import NotGiven


from nti.externalization.extension_points import get_current_request
from nti.externalization.extension_points import set_external_identifiers
from nti.externalization.interfaces import IExternalMappingDecorator


from nti.externalization._base_interfaces import get_standard_external_fields


from nti.externalization.externalization.standard_fields import get_last_modified_time
from nti.externalization.externalization.standard_fields import get_created_time
from nti.externalization.externalization.standard_fields import get_creator
from nti.externalization.externalization.standard_fields import get_container_id
from nti.externalization.externalization.standard_fields import get_class


StandardExternalFields = get_standard_external_fields()


def internal_to_standard_external_dictionary(
        self,
        mergeFrom=None,
        registry=component,
        decorate=True,
        request=NotGiven,
        decorate_callback=NotGiven,
):
    # The real implementation of this function. Code in this
    # package should use this; code outside of this package *MUST NOT*
    # use this---just pass the correct args to to_standard_external_dictionary.
    # This is a temporary name while we transition away from the old arguments.
    result = to_minimal_standard_external_dictionary(self, mergeFrom)

    set_external_identifiers(self, result)

    get_creator(self, None, result)

    get_last_modified_time(self, None, result)
    get_created_time(self, None, result)

    get_container_id(self, None, result)

    if decorate:
        if request is NotGiven:
            request = get_current_request()

        decorate_external_mapping(self, result, registry=registry,
                                  request=request)
    elif callable(decorate_callback):
        decorate_callback(self, result)

    return result

def to_standard_external_dictionary(
        self,
        mergeFrom=None,
        registry=component,
        decorate=True,
        request=NotGiven,
        decorate_callback=NotGiven,
        # These are ignored, present for BWC
        name=NotGiven,
        useCache=NotGiven,
        **kwargs
):
    """
    Returns a dictionary representing the standard externalization of
    the object. This impl takes care of the standard attributes
    including OID (from
    :attr:`~persistent.interfaces.IPersistent._p_oid`) and ID (from
    ``self.id`` if defined) and Creator (from ``self.creator``).

    If the object has any
    :class:`~nti.externalization.interfaces.IExternalMappingDecorator`
    subscribers registered for it, they will be called to decorate the
    result of this method before it returns ( *unless* `decorate` is
    set to False; only do this if you know what you are doing! )

    :param dict mergeFrom: For convenience, if ``mergeFrom`` is not
        None, then those values will be added to the dictionary
        created by this method. The keys and values in ``mergeFrom``
        should already be external.

   .. versionchanged:: 1.0a1
      Arbitrary keyword arguments not used by this function are deprecated
      and produce a warning.
    """

    if kwargs or name is not NotGiven or useCache is not NotGiven: # pragma: no cover
        for _ in range(3):
            warnings.warn(
                "Passing unused arguments to to_standard_external_dictionary will be an error",
                FutureWarning)

    return internal_to_standard_external_dictionary(
        self,
        mergeFrom,
        registry,
        decorate,
        request,
        decorate_callback,
    )


def decorate_external_mapping(self, result, registry=component, request=NotGiven):
    for decorator in registry.subscribers((self,), IExternalMappingDecorator):
        decorator.decorateExternalMapping(self, result)

    if request is NotGiven:
        request = get_current_request()

    if request is not None:
        for decorator in registry.subscribers((self, request), IExternalMappingDecorator):
            decorator.decorateExternalMapping(self, result)

    return result


def to_minimal_standard_external_dictionary(self, mergeFrom=None):
    """
    Does no decoration. Useful for non-'object' types. `self` should have a `mime_type` field.
    """

    result = make_external_dict()
    if mergeFrom is not None:
        result.update_from_other(mergeFrom)
    if StandardExternalFields.CLASS not in result:
        get_class(self, result)

    mime_type = getattr(self, 'mimeType', None) or getattr(self, 'mime_type', None)
    if mime_type is not None and mime_type:
        result[StandardExternalFields.MIMETYPE] = mime_type
    return result


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.externalization._dictionary')
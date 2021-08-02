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


from nti.externalization._base_interfaces import make_external_dict
from nti.externalization._base_interfaces import NotGiven


from nti.externalization.extension_points import set_external_identifiers
from nti.externalization.interfaces import IExternalStandardDictionaryDecorator


from nti.externalization._base_interfaces import get_standard_external_fields
from nti.externalization._base_interfaces import get_default_externalization_policy


from nti.externalization.externalization.standard_fields import get_last_modified_time
from nti.externalization.externalization.standard_fields import get_created_time
from nti.externalization.externalization.standard_fields import get_creator
from nti.externalization.externalization.standard_fields import get_container_id
from nti.externalization.externalization.standard_fields import get_class

from nti.externalization.externalization.decorate import decorate_external_object

StandardExternalFields = get_standard_external_fields()
DEFAULT_EXTERNALIZATION_POLICY = get_default_externalization_policy()

def internal_to_standard_external_dictionary(
        self,
        mergeFrom=None,
        decorate=True,
        request=NotGiven,
        decorate_callback=NotGiven,
        policy=DEFAULT_EXTERNALIZATION_POLICY,
):
    # The real implementation of this function. Code in this
    # package should use this; code outside of this package *MUST NOT*
    # use this---just pass the correct args to to_standard_external_dictionary.
    # This is a temporary name while we transition away from the old arguments.
    result = to_minimal_standard_external_dictionary(self, mergeFrom)

    set_external_identifiers(self, result)

    get_creator(self, None, result)

    get_last_modified_time(self, None, policy, result)
    get_created_time(self, None, policy, result)

    get_container_id(self, None, result)

    decorate_external_object(
        decorate, decorate_callback,
        IExternalStandardDictionaryDecorator, 'decorateExternalMapping',
        self, result,
        None, # unused registry
        request
    )

    return result

def to_standard_external_dictionary(
        self,
        mergeFrom=None,
        registry=NotGiven, # Ignored
        decorate=True,
        request=NotGiven,
        decorate_callback=NotGiven,
        policy=DEFAULT_EXTERNALIZATION_POLICY,
        # These are ignored, present for BWC
        name=NotGiven,
        useCache=NotGiven,
        **kwargs
):
    """to_standard_external_dictionary(self, mergeFrom=None, decorate=True, request=NotGiven)

    Returns a dictionary representing the standard externalization of
    the object *self*. This function takes care of many of the standard external fields:

    * External identifiers like `.StandardExternalFields.OID` and `.StandardExternalFields.NTIID`
      using `.set_external_identifiers`.
    * The `.StandardExternalFields.CREATOR`.
    * The `.StandardExternalFields.LAST_MODIFIED`.
    * The `.StandardExternalFields.CREATED_TIME`.
    * The `.StandardExternalFields.CONTAINER_ID`.
    * The `.StandardExternalFields.CLASS` and `.StandardExternalFields.MIMETYPE`
      (from the ``mimeType`` attribute of the object).

    If the object has any
    :class:`~nti.externalization.interfaces.IExternalStandardDictionaryDecorator`
    subscribers registered for it, they will be called to decorate the
    result of this method before it returns (**unless** *decorate* is
    set to `False`; only do this if you know what you are doing! )
    This is the only part of :mod:`nti.externalization` that invokes this
    decorator.

    Custom externalization should begin by calling this function, or,
    preferably, by using an existing externalizer (which invokes this
    function, such as :class:`~.StandardInternalObjectExternalizer` or
    :class:`~.InterfaceObjectIO` ) or subclassing such an existing
    type and mutating the dictionary returned from super's
    ``toExternalObject`` in your own implementation.

   :keyword dict mergeFrom: For convenience, if *mergeFrom* is not
       `None`, then values it contains will be added to the dictionary
       created by this method. The keys and values in *mergeFrom*
       should already be external.
   :type mergeFrom: dict
   :keyword ExternalizationPolicy policy: The :class:`~.ExternalizationPolicy` to
       use. Must not be None.
   :returns: A `.LocatedExternalDict`. For further externalization,
       this object should be mutated in place.

   .. versionchanged:: 1.0a1
      Arbitrary keyword arguments not used by this function are deprecated
      and produce a warning.
   .. versionchanged:: 2.1
       Add the *policy* keyword.
    """

    if (
            kwargs
            or name is not NotGiven
            or useCache is not NotGiven
            or registry is not NotGiven
    ): # pragma: no cover
        for _ in range(3):
            warnings.warn(
                "Passing unused arguments to to_standard_external_dictionary will be an error",
                FutureWarning)

    return internal_to_standard_external_dictionary(
        self,
        mergeFrom,
        decorate,
        request,
        decorate_callback,
        policy,
    )


def to_minimal_standard_external_dictionary(self, mergeFrom=None):
    """
    Does no decoration. Useful for non-'object' types. *self* should have a *mime_type* field.
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

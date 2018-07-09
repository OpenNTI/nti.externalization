# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Functions related to actually externalizing objects.

Only import from this module. Sub-modules of this package
are implementation details.

"""


# Our request hook function always returns None, and pylint
# flags that as useless (good for it)
# pylint:disable=assignment-from-none

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports

import collections
import warnings

from zope import component

from nti.externalization._base_interfaces import MINIMAL_SYNTHETIC_EXTERNAL_KEYS
from nti.externalization._base_interfaces import isSyntheticKey
from nti.externalization._base_interfaces import NotGiven
from nti.externalization._base_interfaces import PRIMITIVES as _primitives

from nti.externalization.extension_points import get_current_request

from .replacers import NonExternalizableObjectError

from .fields import choose_field

from .standard_fields import SYSTEM_USER_NAME
from .standard_fields import get_last_modified_time
from .standard_fields import get_created_time

from .dictionary import to_standard_external_dictionary
from .dictionary import to_minimal_standard_external_dictionary

from .externalizer import to_external_object

from .decorate import decorate_external_mapping as _decorate_external_mapping

__all__ = [
    'choose_field',
    'NonExternalizableObjectError',
    'get_last_modified_time',
    'get_created_time',

    'to_standard_external_dictionary',
    'to_minimal_standard_external_dictionary',

    'decorate_external_mapping',

    'to_external_object',
    'catch_replace_action',
]


#: Constant requesting JSON format data
EXT_FORMAT_JSON = 'json'


def catch_replace_action(obj, exc):
    """
    Replaces the external component object `obj` with an object noting a broken object.
    """
    __traceback_info__ = obj, exc
    return {"Class": "BrokenExceptionObject"}


def decorate_external_mapping(original_object, external_object,
                              registry=component, request=NotGiven):
    if request is NotGiven:
        request = get_current_request()
    return _decorate_external_mapping(
        original_object, external_object,
        registry, request
    )

# BWC exports

SYSTEM_USER_NAME = SYSTEM_USER_NAME
to_standard_external_created_time = get_created_time
to_standard_external_last_modified_time = get_last_modified_time
isSyntheticKey = isSyntheticKey
toExternalObject = to_external_object


def stripSyntheticKeysFromExternalDictionary(external):
    """
    Given a mutable dictionary, removes all the external keys
    that might have been added by :func:`to_standard_external_dictionary` and echoed back.
    """
    for key in MINIMAL_SYNTHETIC_EXTERNAL_KEYS:
        external.pop(key, None)
    return external


#: This is a deprecated alias
def toExternalDictionary(*args, **kwargs): # pragma: no cover
    warnings.warn("Use to_standard_external_dictionary", FutureWarning)
    return to_standard_external_dictionary(*args, **kwargs)


def is_nonstr_iter(v): # pragma: no cover
    warnings.warn("'is_nonstr_iter' will be deleted. It is broken on Python 3",
                  FutureWarning, stacklevel=2)
    return hasattr(v, '__iter__')


def removed_unserializable(ext):
    # pylint:disable=too-many-branches
    # XXX: Why is this here? We don't use it anymore.
    # Can it be removed?
    warnings.warn("'removed_unserializable' will be deleted.", FutureWarning, stacklevel=2)
    def _is_sequence(m):
        return (not isinstance(m, (str, collections.Mapping))
                and hasattr(m, '__iter__'))

    def _clean(m):
        if isinstance(m, collections.Mapping):
            for k, v in list(m.items()):
                if _is_sequence(v):
                    if not isinstance(v, list):
                        m[k] = list(v)
                elif not isinstance(v, collections.Mapping):
                    if not isinstance(v, _primitives):
                        m[k] = None
            values = m.values()
        elif isinstance(m, list):
            for idx, v in enumerate(m):
                if _is_sequence(v):
                    if not isinstance(v, list):
                        m[idx] = list(v)
                elif not isinstance(v, collections.Mapping):
                    if not isinstance(v, _primitives):
                        m[idx] = None
            values = m
        else:
            values = ()
        for x in values:
            _clean(x)
    if _is_sequence(ext) and not isinstance(ext, list):
        ext = list(ext)
    _clean(ext)
    return ext

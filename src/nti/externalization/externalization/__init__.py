# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Functions related to actually externalizing objects.


"""
# There are a *lot* of fixme (XXX and the like) in this file.
# Turn those off in general so we can see through the noise.
# pylint:disable=fixme

# Our request hook function always returns None, and pylint
# flags that as useless (good for it)
# pylint:disable=assignment-from-none

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports

import collections
import warnings


from nti.externalization._base_interfaces import MINIMAL_SYNTHETIC_EXTERNAL_KEYS
from nti.externalization._base_interfaces import isSyntheticKey
from nti.externalization._base_interfaces import PRIMITIVES as _primitives


from .replacers import NonExternalizableObjectError

from .fields import choose_field
from .fields import SYSTEM_USER_NAME

from .standard_fields import get_last_modified_time
from .standard_fields import get_created_time

from .dictionary import to_standard_external_dictionary
from .dictionary import to_minimal_standard_external_dictionary
from .dictionary import decorate_external_mapping

from .externalizer import to_external_object


#: Constant requesting JSON format data
EXT_FORMAT_JSON = 'json'




__all__ = [
    'choose_field',
    'NonExternalizableObjectError',
    'get_last_modified_time',
    'get_created_time',

    'to_standard_external_dictionary',
    'to_minimal_standard_external_dictionary',
    'decorate_external_mapping', # XXX: Maybe in a new file?

    'to_external_object',
    'catch_replace_action',
]

def catch_replace_action(obj, exc):
    """
    Replaces the external component object `obj` with an object noting a broken object.
    """
    __traceback_info__ = obj, exc
    return {"Class": "BrokenExceptionObject"}


# BWC exports

SYSTEM_USER_NAME = SYSTEM_USER_NAME
to_standard_external_created_time = get_created_time
to_standard_external_last_modified_time = get_last_modified_time
isSyntheticKey = isSyntheticKey
toExternalObject = to_external_object

logger = __import__('logging').getLogger(__name__)



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


def is_nonstr_iter(v):
    warnings.warn("'is_nonstr_iter' will be deleted.", FutureWarning)
    return hasattr(v, '__iter__')


def removed_unserializable(ext):
    # pylint:disable=too-many-branches
    # XXX: Why is this here? We don't use it anymore.
    # Can it be removed?
    warnings.warn("'removed_unserializable' will be deleted.", FutureWarning)
    def _is_sequence(m):
        return not isinstance(m, collections.Mapping) and is_nonstr_iter(m)

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

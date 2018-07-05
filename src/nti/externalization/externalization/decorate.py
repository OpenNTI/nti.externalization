# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for decorating external objects.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Our request hook function always returns None, and pylint
# flags that as useless (good for it)
# pylint:disable=assignment-from-none


from nti.externalization.extension_points import get_current_request
from nti.externalization._base_interfaces import NotGiven
from nti.externalization.interfaces import IExternalMappingDecorator


def decorate_external_object(do_decorate, call_if_not_decorate,
                             decorate_interface, decorate_meth_name,
                             original_object, external_object,
                             registry, request):
    if do_decorate:
        for decorator in registry.subscribers((original_object,), decorate_interface):
            meth = getattr(decorator, decorate_meth_name)
            meth(original_object, external_object)

        if request is NotGiven:
            request = get_current_request()

        if request is not None:
            # Request specific decorating, if given, is more specific than plain object
            # decorating, so it gets to go last.
            for decorator in registry.subscribers((original_object, request), decorate_interface):
                meth = getattr(decorator, decorate_meth_name)
                meth(original_object, external_object)
    elif call_if_not_decorate is not NotGiven and call_if_not_decorate is not None:
        # XXX: This makes no sense. What is this argument even for?
        call_if_not_decorate(original_object, external_object)

    return external_object

def decorate_external_mapping(original_object, external_object, registry, request):
    # A convenience API exposed to Python in __init__.py
    return decorate_external_object(
        True, None,
        IExternalMappingDecorator, 'decorateExternalMapping',
        original_object, external_object,
        registry, request
    )

from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.externalization._decorate')

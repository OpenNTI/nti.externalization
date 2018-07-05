# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Finding fields of an object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function




from nti.externalization._base_interfaces import get_standard_external_fields

logger = __import__('logging').getLogger(__name__)

StandardExternalFields = get_standard_external_fields()

def choose_field(result, self, ext_name,
                 converter=None,
                 fields=(),
                 sup_iface=None, sup_fields=(), sup_converter=None):
    # XXX: We have a public user of this in nti.ntiids.oids. We need
    # to document this and probably move it to a different module, or
    # provide a cleaner simpler replacement.
    for x in fields:
        value = getattr(self, x, None)
        if value is None:
            continue

        if converter is not None:
            value = converter(value)
        if value is not None:
            result[ext_name] = value
            return value


    # Nothing. Can we adapt it?
    if sup_iface is not None and sup_fields:
        self = sup_iface(self, None)
        if self is not None:
            return choose_field(result, self, ext_name,
                                converter=sup_converter,
                                fields=sup_fields)

    # Falling off the end: return None
    return None


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.externalization._fields')

# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Finding fields of an object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from six import text_type

from zope.security.management import system_user
from zope.security.interfaces import IPrincipal

from ZODB.POSException import POSKeyError

from nti.externalization._base_interfaces import get_standard_external_fields

logger = __import__('logging').getLogger(__name__)

StandardExternalFields = get_standard_external_fields()
identity = lambda obj: obj


_SYSTEM_USER_NAME = getattr(system_user, 'title').lower()
SYSTEM_USER_NAME = _SYSTEM_USER_NAME # Export from cython to python
_SYSTEM_USER_ID = system_user.id
del system_user

IPrincipal_providedBy = IPrincipal.providedBy
del IPrincipal

def is_system_user(obj):
    return IPrincipal_providedBy(obj) and obj.id == _SYSTEM_USER_ID


def choose_field(result, self, ext_name,
                 converter=None,
                 fields=(),
                 sup_iface=None, sup_fields=(), sup_converter=None):
    # XXX: We have a public user of this in nti.ntiids.oids. We need
    # to document this and probably move it to a different module, or
    # provide a cleaner simpler replacement.
    for x in fields:
        try:
            value = getattr(self, x)
        except AttributeError:
            continue
        except POSKeyError:
            logger.exception("Could not get attribute %s for object %s",
                             x, self)
            continue

        if value is not None:
            # If the creator is the system user, catch it here
            # XXX: Document this behaviour.
            if ext_name == StandardExternalFields.CREATOR:
                if is_system_user(value):
                    value = SYSTEM_USER_NAME
                else:
                    # This is a likely recursion point, we want to be
                    # sure we don't do that.
                    value = text_type(value)
                result[ext_name] = value
                return value
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

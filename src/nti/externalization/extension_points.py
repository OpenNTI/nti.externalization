# -*- coding: utf-8 -*-
"""
Extension points for integrating with other applications,
frameworks, and libraries.

The normal extension mechanisms for this package are :mod:`zope.component`
and :mod:`zope.interface`. The particular extension points found here
are different for two reasons:

1. There is expected to be only one way that a given application will
   want to configure the extension point.

2. They are believed to be so performance critical to normal
   operations that the use of a component utility lookup would be
   noticeably detrimental.

For those two reasons, these extension points are both developed with
:mod:`zope.hookable`, which provides a very low-overhead way to invoke
a function while allowing for it to be extended. Applications that
need to changed the behaviour of the built-in functions supplied here will
need to call their :func:`zope.hookable.hookable.sethook` method at
startup.

.. versionadded:: 1.0

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.hookable import hookable

from ._compat import to_unicode
from .oids import to_external_oid
from .interfaces import StandardExternalFields

__all__ = [
    'get_current_request',
    'set_external_identifiers',
]

@hookable
def get_current_request():
    """
    get_current_request() -> request

    In a request/response system like a WSGI server,
    return an object representing the current request.

    In some cases, this may be used to find adapters for objects.
    It is also passed to the ``toExternalObject`` function of
    each object as a keyword parameter.

    In version 1.0, this will default to using Pyramid's
    :func:`pyramid.threadlocal.get_current_request` if pyramid is
    installed. However, in a future version, an application wishing
    to use Pyramid's request will explicitly need to set the hook.

    .. deprecated:: 1.0
       The automatic fallback to Pyramid. It will be removed
       in 1.1 or before.
    """
    return None # pragma: no cover


try:
    from pyramid import threadlocal
except ImportError:
    pass
else: # pragma: no cover
    get_current_request.sethook(threadlocal.get_current_request)
    del threadlocal


_StandardExternalFields_OID = StandardExternalFields.OID
_StandardExternalFields_NTIID = StandardExternalFields.NTIID
del StandardExternalFields


@hookable
def set_external_identifiers(self, result):
    """
    set_external_identifiers(self, result) -> None

    Place the stable external identifiers for *self* in the dictionary
    *result*.

    By default, this function uses the result of `.to_external_oid` as
    the value to put in *result*, under the keys
    `~nti.externalization._base_interfaces.StandardExternalFields.OID`
    as well as `~nti.externalization._base_interfaces.StandardExternalFields.NTIID`.

    This is called from `to_standard_external_dictionary`, a default
    part of producing the external dictionary for all objects.
    """
    ntiid = oid = to_unicode(to_external_oid(self))
    if ntiid:
        result[_StandardExternalFields_OID] = oid
        result[_StandardExternalFields_NTIID] = ntiid
    return (oid, ntiid)

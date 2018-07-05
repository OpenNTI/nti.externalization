# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions to find standard fields.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint:disable=inconsistent-return-statements

from calendar import timegm as dt_tuple_to_unix

from zope.dublincore.interfaces import IDCTimes

from nti.externalization._base_interfaces import get_standard_external_fields
from nti.externalization._base_interfaces import get_standard_internal_fields

from .fields import choose_field

StandardExternalFields = get_standard_external_fields()
StandardInternalFields = get_standard_internal_fields()


def datetime_to_unix_time(dt):
    if dt is not None:
        return dt_tuple_to_unix(dt.utctimetuple())


_LAST_MOD_FIELDS = (
    StandardInternalFields.LAST_MODIFIED,
    StandardInternalFields.LAST_MODIFIEDU
)

_LAST_MOD_SUP_FIELDS = (
    'modified',
)

def get_last_modified_time(context, default=None, _write_into=None):
    """
    Find and return a number representing the time since the epoch
    in fractional seconds at which the ``context`` was last modified.
    This is the same value that is used by :func:`to_standard_external_dictionary`,
    and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
    or :class:`zope.dublincore.interfaces.IDCTimes`.

    :return: A number if it can be found, or the value of ``default``
    """
    # The _write_into argument is for the benefit of
    # to_standard_external_dictionary
    holder = _write_into if _write_into is not None else {}

    choose_field(holder, context, StandardExternalFields.LAST_MODIFIED,
                 None,
                 _LAST_MOD_FIELDS,
                 # sup_iface, sup_fields, sup_converter
                 IDCTimes, _LAST_MOD_SUP_FIELDS, datetime_to_unix_time)
    return holder.get(StandardExternalFields.LAST_MODIFIED, default)


_CREATED_TIME_FIELDS = (
    StandardInternalFields.CREATED_TIME,
)

_CREATED_TIME_SUP_FIELDS = (
    'created',
)

def get_created_time(context, default=None, _write_into=None):
    """
    Find and return a number representing the time since the epoch
    in fractional seconds at which the ``context`` was created.
    This is the same value that is used by :func:`to_standard_external_dictionary`,
    and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
    or :class:`zope.dublincore.interfaces.IDCTimes`.

    :return: A number if it can be found, or the value of ``default``
    """
    # The _write_into argument is for the benefit of
    # to_standard_external_dictionary
    holder = _write_into if _write_into is not None else {}

    choose_field(holder, context, StandardExternalFields.CREATED_TIME,
                 None,
                 _CREATED_TIME_FIELDS,
                 # sup_iface, sup_fields, sup_converter
                 IDCTimes, _CREATED_TIME_SUP_FIELDS, datetime_to_unix_time)

    return holder.get(StandardExternalFields.CREATED_TIME, default)


_CREATOR_FIELDS = (
    StandardInternalFields.CREATOR,
    StandardExternalFields.CREATOR,
)

def get_creator(context, default=None, _write_into=None):
    holder = _write_into if _write_into is not None else {}

    choose_field(holder, context, StandardExternalFields.CREATOR,
                 None,
                 _CREATOR_FIELDS)

    return holder.get(StandardExternalFields.CREATOR, default)


_CONTAINER_FIELDS = (
    StandardInternalFields.CONTAINER_ID,
)

def get_container_id(context, default=None, _write_into=None):
    holder = _write_into if _write_into is not None else {}
    containerId = choose_field(holder, context, StandardExternalFields.CONTAINER_ID,
                               None,
                               _CONTAINER_FIELDS)
    if containerId is not None:
        # alias per mobile client request 20150625
        holder[StandardInternalFields.CONTAINER_ID] = containerId

    return holder.get(StandardExternalFields.CONTAINER_ID, default)




_EXT_CLASS_IGNORED_MODULES = (
    'nti.externalization',
    'nti.externalization.datastructures',
    'nti.externalization.persistence',
    'nti.externalization.interfaces',
    'nti.externalization._base_interfaces',
    'nti.externalization.__base_interfaces',
)

def get_class(context, _write_into=None):
    holder = _write_into if _write_into is not None else {}

    cls = getattr(context, '__external_class_name__', None)
    if cls is not None and cls:
        holder[StandardExternalFields.CLASS] = cls
    else:
        class_ = context.__class__
        class_name = class_.__name__
        if (not class_name.startswith('_')
                and class_.__module__ not in _EXT_CLASS_IGNORED_MODULES):
            cls = holder[StandardExternalFields.CLASS] = class_name

    return cls



from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.externalization._standard_fields')

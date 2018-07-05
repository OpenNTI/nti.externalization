#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for reading and writing date and time related objects.

See the :mod:`datetime` module, as well as the :mod:`zope.interface.common.idatetime`
module for types of objects.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
from datetime import datetime
import sys
import time

import isodate
import pytz
import six
from zope import component
from zope import interface
from zope.interface.common.idatetime import IDate
from zope.interface.common.idatetime import IDateTime
from zope.interface.common.idatetime import ITimeDelta

from nti.externalization.interfaces import IInternalObjectExternalizer
from nti.schema.interfaces import InvalidValue


def _parse_with(func, string):
    try:
        return func(string)
    except isodate.ISO8601Error as e:
        e = InvalidValue(*e.args, value=string)
        six.reraise(InvalidValue, e, sys.exc_info()[2])

_input_type = (str if sys.version_info[0] >= 3 else basestring)
# XXX: This should really be either unicode or str on Python 2. We need to *know*
# what our input type is. All the tests pass on Python 3 with this registered to 'str'.
@component.adapter(_input_type)
@interface.implementer(IDate)
def _date_from_string(string):
    """
    This adapter allows any field which comes in as a string is
    IOS8601 format to be transformed into a date. The schema field
    must be an ``Object`` field with a type of ``IDate``

    If you need a schema field that accepts human input, rather than
    programattic input, you probably want to use a custom field that
    uses :func:`zope.datetime.parse` in its ``fromUnicode`` method.
    """
    # This:
    #   datetime.date.fromtimestamp( zope.datetime.time( string ) )
    # is simple, but seems to have confusing results, depending on what the
    # timezone is? If we put in "1982-01-31" we get back <1982-01-30>
    # This:
    #   parsed = zope.datetime.parse( string )
    #   return datetime.date( parsed[0], parsed[1], parsed[2] )
    # accepts almost anything as a date (so it's great for human interfaces),
    # but programatically we actually require ISO format
    return _parse_with(isodate.parse_date, string)


def _pytz_timezone(key):
    try:
        return pytz.timezone(key)
    except (KeyError, AttributeError):
        return None


def _local_tzinfo(local_tzname=None):
    # They did not specify a timezone, assume they authored
    # in the native timezone, meaning to use any DST rules in
    # effect at the time specified, not the current time.
    local_tzname = local_tzname or time.tzname
    tzinfo = _pytz_timezone(local_tzname)

    # Ok, not a value known to pytz. Is it a two-tuple like ('CST', 'CDT')
    # that we can figure out the offset of ourself?
    if (not tzinfo
            and isinstance(local_tzname, tuple)
            and len(local_tzname) == 2
            and all((bool(x) for x in local_tzname))):
        offset_hours = time.timezone // 3600
        local_tzname = '%s%d%s' % (local_tzname[0],
                                   offset_hours,
                                   local_tzname[1])
        tzinfo = _pytz_timezone(local_tzname)

    if not tzinfo:
        # well nuts. Do the best we can with the current info
        # First, get the timezone name, using daylight name if appropriate
        offset = (time.altzone
                  if time.daylight and time.altzone is not None and time.tzname[1]
                  else time.timezone)

        add = '+' if offset > 0 else ''
        local_tzname = 'Etc/GMT' + add + str((offset // 60 // 60))
        tzinfo = pytz.timezone(local_tzname)
    return tzinfo


def _as_utc_naive(dt, assume_local=True, local_tzname=None):
    # Now convert to GMT, but as a 'naive' object.
    if not dt.tzinfo:
        if assume_local:
            tzinfo = _local_tzinfo(local_tzname)
            dt = tzinfo.localize(dt)
        else:
            dt = dt.replace(tzinfo=pytz.UTC)
    # Convert to UTC, then back to naive
    dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
    return dt


@component.adapter(_input_type)
@interface.implementer(IDateTime)
def datetime_from_string(string, assume_local=False, local_tzname=None):
    """
    This adapter allows any field which comes in as a string is
    IOS8601 format to be transformed into a datetime. The schema field
    should be an ``Object`` field with a type of ``IDateTime`` or an
    instance of ``ValidDateTime``. Wrap this with an
    ``AdaptingFieldProperty``.

    Datetime values produced by this object will always be in GMT/UTC
    time, and they will always be datetime naive objects.

    If you need a schema field that accepts human input, rather than
    programattic input, you probably want to use a custom field that
    uses :func:`zope.datetime.parse` in its ``fromUnicode`` method.

    :keyword assume_local: If `False`, the default, then when
            we parse a string that does not include timezone information,
            we will assume that it is already meant to be in UTC.
            Otherwise, if set to true, when we parse such a string we
            will assume that it is meant to be in the \"local\" timezone
            and adjust accordingly. If the local timezone experiences
            DST, then the time will be interpreted with the UTC offset
            *as-of the DST rule in effect on the date parsed*, not
            the current date, if possible. If not possible, the current
            rule will be used.
    :keyword local_tzname: If given, either a string acceptable to
            :func:`pytz.timezone` to produce a ``tzinfo`` object,
            or a two-tuple as given from :const:`time.timezone`. If not given,
            local timezone will be determined automatically.
    """
    dt = _parse_with(isodate.parse_datetime, string)
    return _as_utc_naive(dt, assume_local=assume_local, local_tzname=local_tzname)


@component.adapter(int)
@component.adapter(float)
@interface.implementer(IDateTime)
def datetime_from_timestamp(value):
    return datetime.utcfromtimestamp(value)


@component.adapter(IDate)
@interface.implementer(IInternalObjectExternalizer)
class _date_to_string(object):
    """
    Produce an IOS8601 string from a date.
    """

    def __init__(self, date):
        self.date = date

    def toExternalObject(self, **unused_kwargs):
        return isodate.date_isoformat(self.date)


@component.adapter(IDateTime)
@interface.implementer(IInternalObjectExternalizer)
class _datetime_to_string(object):
    """
    Produce an IOS8601 string from a datetime
    """

    def __init__(self, date):
        self.date = date

    def toExternalObject(self, **unused_kwargs):
        # Convert to UTC, assuming that a missing timezone
        # is already in UTC
        dt = _as_utc_naive(self.date, assume_local=False)
        # indicate it is UTC on the wire
        return isodate.datetime_isoformat(dt) + 'Z'


@component.adapter(ITimeDelta)
@interface.implementer(IInternalObjectExternalizer)
class _duration_to_string(object):
    """
    Produce an IOS8601 format duration from a :class:`datetime.timedelta`
    object.

    Timedelta objects do not represent years or months (the biggest
    duration they accept is weeks) and internally they normalize
    everything to days and smaller. Thus, the format produced by this
    transformation will never have a field larger than days.
    """

    def __init__(self, date):
        self.date = date

    def toExternalObject(self, **unused_kwargs):
        return isodate.duration_isoformat(self.date)

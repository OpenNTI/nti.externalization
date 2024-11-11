#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External representation support.

The provided implementations of
`~nti.externalization.interfaces.IExternalObjectIO` live here. We
provide and register two, one for `JSON <.EXT_REPR_JSON>` and one for
`YAML <.EXT_REPR_YAML>`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import decimal
import warnings

from persistent import Persistent
from ZODB.POSException import POSError
import simplejson
import yaml
from zope import component
from zope import interface

from ._base_interfaces import NotGiven as _NotGiven
from .externalization import toExternalObject
from .interfaces import EXT_REPR_JSON
from .interfaces import EXT_REPR_YAML
from .interfaces import IExternalObjectIO
from .interfaces import IExternalObjectRepresenter

__all__ = [
    'to_external_representation',
    'to_json_representation',
    'WithRepr',
]

# Driver functions


def to_external_representation(obj, ext_format=EXT_REPR_JSON,
                               name=_NotGiven, registry=_NotGiven):
    """
    to_external_representation(obj, ext_format='json', name=NotGiven) -> str

    Transforms (and returns) the *obj* into its external (string)
    representation.

    Uses :func:`nti.externalization.to_external_object`, passing in the *name*.

    :param str ext_format: One of
        `.EXT_REPR_JSON` or
        `.EXT_REPR_YAML`, or the
        name of some other utility that implements
        `~nti.externalization.interfaces.IExternalObjectRepresenter`
    """
    if registry is not _NotGiven: # pragma: no cover
        warnings.warn(
            "The registry argument is ignored. Call in a correct site.",
            FutureWarning
        )
    # It would seem nice to be able to do this in one step during
    # the externalization process itself, but we would wind up traversing
    # parts of the datastructure more than necessary. Here we traverse
    # the whole thing exactly twice.
    ext = toExternalObject(obj, name=name)
    return component.getUtility(IExternalObjectRepresenter, name=ext_format).dump(ext)


def to_json_representation(obj):
    """
    A convenience function that calls
    :func:`to_external_representation` with `.EXT_REPR_JSON`.
    """
    return to_external_representation(obj, EXT_REPR_JSON)


# JSON

def _second_pass_to_external_object(obj):
    result = toExternalObject(obj, name='second-pass')
    if result is obj:
        raise TypeError(repr(obj) + " is not serializable")
    return result


@interface.named(EXT_REPR_JSON)
@interface.implementer(IExternalObjectIO)
class JsonRepresenter(object):

    _DUMP_ARGS = dict(check_circular=False,
                      sort_keys=__debug__,  # Makes testing easier
                      default=_second_pass_to_external_object)

    def dump(self, obj, fp=None):
        """
        Given an object that is known to already be in an externalized form,
        convert it to JSON. This can be about 10% faster then requiring a pass
        across all the sub-objects of the object to check that they are in external
        form, while still handling a few corner cases with a second-pass conversion.
        (These things creep in during the object decorator phase and are usually
        links.)
        """
        if fp:
            return simplejson.dump(obj, fp, **self._DUMP_ARGS)

        return simplejson.dumps(obj, **self._DUMP_ARGS)

    def load(self, stream):
        # We need all string values to be unicode objects. simplejson is different from
        # the built-in json and returns strings that can be represented as ascii as str
        # objects if the input was a bytestring.
        # The only way to get it to return unicode is if the input is unicode, or
        # to use a hook to do so incrementally. The hook saves allocating the entire request body
        # as a unicode string in memory and is marginally faster in some cases. However,
        # the hooks gets to be complicated if it correctly catches everything (inside arrays,
        # for example; the function below misses them) so decoding to unicode up front
        # is simpler

        if isinstance(stream, bytes):
            stream = stream.decode('utf-8')
        value = simplejson.loads(stream, allow_nan=True)

        # Depending on whether the simplejson C speedups are active, we can still
        # get back a non-unicode string if the object was a naked string. (If the python
        # version is used, it returns unicode; the C version returns str.)
        if isinstance(value, bytes):
            # we know it's simple ascii or it would have produced unicode
            value = value.decode("ascii")
        return value
to_json_representation_externalized = JsonRepresenter().dump


# YAML

class _ExtDumper(yaml.SafeDumper):
    """
    We want to represent all of our special object types,
    like LocatedExternalList/Dict and the ContentFragment subtypes,
    as plain yaml data structures.

    Therefore we must register their base types as multi-representers.
    """

# The difference between 'add_representer' and 'add_multi_representer'
# is that the multi version accepts subclasses, but the plain version
# requires an exact type match.
_ExtDumper.add_multi_representer(list, _ExtDumper.represent_list)
_ExtDumper.add_multi_representer(dict, _ExtDumper.represent_dict)
if str is bytes: # Python 2
     # pylint:disable=undefined-variable,no-member
    _ExtDumper.add_multi_representer(unicode, _ExtDumper.represent_unicode)
else: # Python 3
    _ExtDumper.add_multi_representer(str, _ExtDumper.represent_str)

def _yaml_represent_decimal(dumper, data):
    s = str(data)
    if '.' not in s:
        try:
            int(s)
        except ValueError:
            pass
        else:
            return dumper.represent_int(data)
    if data.is_nan():
        return dumper.represent_float(float('nan'))
    if data.is_infinite():
        return dumper.represent_float(float('-inf') if data.is_signed() else float('+inf'))
    return dumper.represent_scalar('tag:yaml.org,2002:float', str(data).lower())
_ExtDumper.add_representer(decimal.Decimal, _yaml_represent_decimal)

# PyYAML uses the multi dumper on ``None`` as the fallback when
# nothing else can be found.
def _yaml_represent_unknown(dumper, data):
    ext_obj = _second_pass_to_external_object(data)
    return dumper.represent_data(ext_obj)
_ExtDumper.add_multi_representer(None, _yaml_represent_unknown)



class _UnicodeLoader(yaml.SafeLoader):

    def construct_yaml_str(self, node):
        # yaml defines strings to be unicode, but
        # the default reader encodes anything that can be
        # represented as ASCII back to bytes. We don't
        # want that.
        return self.construct_scalar(node)
_UnicodeLoader.add_constructor('tag:yaml.org,2002:str',
                               _UnicodeLoader.construct_yaml_str)


@interface.named(EXT_REPR_YAML)
@interface.implementer(IExternalObjectIO)
class YamlRepresenter(object):

    def dump(self, obj, fp=None):
        # The default_flow_style changed in PyYaml 5.1 from None to False.
        # Using False produces multi-line, indented, verbose output. While being human readable,
        # this consumes space and eliminates simple parsing with JSON. Using True
        # produces JSON-compatible output in many cases. Using None (the old default)
        # produces backwards-compatible output that's a hybrid of indented and JSON-like.
        # https://github.com/yaml/pyyaml/issues/199
        return yaml.dump(obj, stream=fp, Dumper=_ExtDumper, default_flow_style=True)

    def load(self, stream):
        return yaml.load(stream, Loader=_UnicodeLoader)


# Misc

def _type_name(self):
    t = type(self)
    type_name = t.__module__ + '.' + t.__name__
    return type_name

def _default_repr(self):
    # When we're executing, even if we're wrapped in a proxy when called,
    # we get an unwrapped self.
    return "<%s at %x %s>" % (_type_name(self), id(self), self.__dict__)

def make_repr(default=_default_repr):
    default = default if callable(default) else _default_repr
    def __repr__(self):
        try:
            return default(self)
        except POSError as cse:
            return '<%s(Ghost, %r)>' % (_type_name(self), cse)
        except (ValueError, LookupError, AttributeError) as e:
            # Things like invalid NTIID, missing registrations for the first two.
            # The final would be a  weird database-related issue.
            return '<%s(%r)>' % (_type_name(self), e)

    return __repr__

class _PReprException(Exception):
    # Raised for the sole purpose of carrying a smuggled
    # repr.
    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __repr__(self):
        return self.value


def _add_repr_to_cls(cls, default=_default_repr):
    if issubclass(cls, Persistent):
        # Persistent 4.4 includes the OID and JAR repr
        # by default, and catches all the exceptions that our
        # make_repr would catch, handling them much better. We only want the
        # __dict__ in there by default, though
        if default is _default_repr:
            default = lambda self: repr(self.__dict__) # pylint:disable=unnecessary-lambda-assignment

        def _p_repr(self):
            raise _PReprException(default(self))

        cls._p_repr = _p_repr # pylint:disable=protected-access
    else:
        cls.__repr__ = make_repr(default)

    return cls

def WithRepr(default=_default_repr):
    """
    A class decorator factory to give a ``__repr__`` to
    the object. Useful for persistent objects.

    :param default: A callable to be used for the default value.
    """

    # If we get one argument that is a type, we were
    # called bare (@WithRepr), so decorate the type
    if isinstance(default, type):
        return _add_repr_to_cls(default)

    # If we got None or anything else, we were called as a factory,
    # so return a decorator
    return lambda cls: _add_repr_to_cls(cls, default)

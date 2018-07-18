# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for validating and setting individual fields
(attributes) of an object.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint:disable=protected-access

# stdlib imports
from sys import exc_info as get_exc_info

from six import text_type
from six import reraise

from zope.interface import implementedBy

from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import SchemaNotProvided
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import WrongContainedType
from zope.schema.interfaces import WrongType

from zope.schema.fieldproperty import FieldProperty
from zope.schema.fieldproperty import NO_VALUE
from zope.schema.fieldproperty import FieldUpdatedEvent

from zope.event import notify

IField_providedBy = IField.providedBy
IFromUnicode_providedBy = IFromUnicode.providedBy

__all__ = [
    'validate_field_value',
    'validate_named_field_value',
]

def noop():
    return


class SetattrSet(object):
    """
    A callable object that uses ``setattr`` to set an
    attribute on an object.
    """

    # Needed because Cython had issues compiling the anonymous
    # lambda closures we previously used.

    __slots__ = (
        'ext_self',
        'field_name',
        'value',
    )

    def __init__(self, ext_self, field_name, value):
        self.ext_self = ext_self
        self.field_name = field_name
        self.value = value

    def __call__(self):
        setattr(self.ext_self, self.field_name, self.value)

class FieldSet(object):
    """
    A callable object that uses ``field.set`` to set an
    attribute on an object.
    """

    # See SetattrSet for the justification.

    __slots__ = (
        'ext_self',
        'field',
        'value'
    )

    def __init__(self, ext_self, field, value):
        self.ext_self = ext_self
        # Don't denormalize field.set; there's a tiny
        # chance we won't actually be called.
        # The field must already be bound to ext_self, and
        # the value must already be valid.
        self.field = field
        self.value = value

    def __call__(self):
        # We monkey-patch FieldProperty so we can avoid double
        # validation, which can be quite expensive in benchmarks.
        # (See below.)

        # The object we're updating is either newly created or
        # otherwise local to this thread, so there shouldn't be any
        # race conditions here. We also generally don't expect to be used
        # with objects that have limited __slots__ and no __dict__
        self.ext_self._v_bound_field_already_valid = self.field
        try:
            self.field.set(self.ext_self, self.value)
        finally:
            del self.ext_self._v_bound_field_already_valid


_FieldProperty_orig_set = FieldProperty.__set__

def _FieldProperty__set__valid(self, inst, value):
    valid_field = getattr(inst, '_v_bound_field_already_valid', None)
    if valid_field is not None:
        # Skip the validation, but do everything else just like
        # FieldProperty does.
        oldvalue = self.queryValue(inst, NO_VALUE)
        inst.__dict__[self._FieldProperty__name] = value
        notify(FieldUpdatedEvent(inst, valid_field, oldvalue, value))
    else:
        _FieldProperty_orig_set(self, inst, value)

_FieldProperty__set__valid.orig_func = _FieldProperty_orig_set

# Detect the case that we're in Cython compiled code, where
# we've already replaced the __set__ function with our own.
if FieldProperty.__set__.__name__ == _FieldProperty__set__valid.__name__: # pragma: no cover
    _FieldProperty_orig_set = FieldProperty.__set__.orig_func
    _FieldProperty__set__valid.org_func = _FieldProperty_orig_set

FieldProperty.__set__ = _FieldProperty__set__valid



class CannotConvertSequenceError(TypeError):
    """
    A TypeError raised when we are asked to convert a sequence
    but we don't know how.
    """

def _adapt_sequence(field, value):
    # IObject provides `schema`, which is an interface, so we can adapt
    # using it. Some other things do not, for example nti.schema.field.Variant
    # They might provide a `fromObject` function to do the conversion
    # The field may be able to handle the whole thing by itself or we may need
    # to do the individual objects

    # The conversion process may raise TypeError
    if hasattr(field, 'fromObject'):
        value = field.fromObject(value)
    else:
        if hasattr(field.value_type, 'fromObject'):
            converter = field.value_type.fromObject
        elif hasattr(field.value_type, 'schema'):
            converter = field.value_type.schema
        else:
            raise CannotConvertSequenceError(
                "Don't know how to convert sequence %r for field %s"
                % (value, field))

        value = [converter(v) for v in value]

    return value


def _all_SchemaNotProvided(sequence):
    for ex in sequence:
        if not isinstance(ex, SchemaNotProvided):
            return False # pragma: no cover
    return True

###
# Fixup functions for various validation errors.
# Because these are called as separate functions *after* the
# exception is caught, the fact that they each take a reference to the
# exception's traceback does not introduce cycles. (Also it helps
# that these are compiled with Cython, which doesn't use frame objects
# in the traceback.) So we don't bother with the usual try/finally: del
###

def _handle_SchemaNotProvided(field_name, field, value):
    # The object doesn't implement the required interface.
    # Can we adapt the provided object to the desired interface?
    # First, capture the details so we can reraise if needed
    exc_info = get_exc_info()
    if not exc_info[1].args:  # zope.schema doesn't fill in the details, which sucks
        exc_info[1].args = (field_name, field.schema)

    try:
        value = field.schema(value)
        field.validate(value)
        return value
    except (LookupError, TypeError, ValidationError, AttributeError):
        # Nope. TypeError (or AttrError - Variant) means we couldn't adapt,
        # and a validation error means we could adapt, but it still wasn't
        # right. Raise the original SchemaValidationError.
        reraise(*exc_info)

def _handle_WrongType(field_name, field, value):
    # Like SchemaNotProvided, but for a primitive type,
    # most commonly a date
    # Can we adapt?
    exc_info = get_exc_info()

    if len(exc_info[1].args) != 3: # pragma: no cover
        reraise(*exc_info)

    exp_type = exc_info[1].args[1]
    implemented_by_type = list(implementedBy(exp_type))
    # If the type unambiguously implements an interface (one interface)
    # that's our target. IDate does this
    if len(implemented_by_type) != 1:
        reraise(*exc_info)

    schema = implemented_by_type[0]

    try:
        return schema(value)
    except (LookupError, TypeError):
        # No registered adapter, darn
        raise reraise(*exc_info)
    except ValidationError as e:
        # Found an adapter, but it does its own validation,
        # and that validation failed (eg, IDate below)
        # This is still a more useful error than WrongType,
        # so go with it after ensuring it has a field
        e.field = field
        raise


def _handle_WrongContainedType(field_name, field, value):
    # We failed to set a sequence. This would be of simple (non externalized)
    # types.
    # Try to adapt each value to what the sequence wants, just as above,
    # if the error is one that may be solved via simple adaptation
    # TODO: This is also thrown from IObject fields when validating the
    # fields of the object
    exc_info = get_exc_info()

    if not exc_info[1].args or not _all_SchemaNotProvided(exc_info[1].args[0]):
        reraise(*exc_info)

    # IObject provides `schema`, which is an interface, so we can adapt
    # using it. Some other things do not, for example nti.schema.field.Variant
    # They might provide a `fromObject` function to do the conversion
    # The field may be able to handle the whole thing by itself or we may need
    # to do the individual objects

    try:
        value = _adapt_sequence(field, value)
    except TypeError:
        # TypeError means we couldn't adapt, in which case we want
        # to raise the original error. If we could adapt,
        # but the converter does its own validation (e.g., fromObject)
        # then we want to let that validation error rise
        raise reraise(*exc_info)

    # Now try to validate the converted value
    try:
        field.validate(value)
    except ValidationError:
        # Nope. TypeError means we couldn't adapt, and a
        # validation error means we could adapt, but it still wasn't
        # right. Raise the original SchemaValidationError.
        raise reraise(*exc_info)

    return value

def validate_field_value(self, field_name, field, value):
    """
    Given a :class:`zope.schema.interfaces.IField` object from a schema
    implemented by `self`, validates that the proposed value can be
    set. If the value needs to be adapted to the schema type for validation to work,
    this method will attempt that.

    :param string field_name: The name of the field we are setting. This
            implementation currently only uses this for informative purposes.
    :param field: The schema field to use to validate (and set) the value.
    :type field: :class:`zope.schema.interfaces.IField`

    :raises zope.interface.Invalid: If the field cannot be validated,
            along with a good reason (typically better than simply provided by the field itself)
    :return: A callable of no arguments to call to actually set the value (necessary
            in case the value had to be adapted).
    """
    __traceback_info__ = field_name, value
    field = field.bind(self)
    try:
        if isinstance(value, text_type) and IFromUnicode_providedBy(field):
            value = field.fromUnicode(value)  # implies validation
        else:
            field.validate(value)
    except SchemaNotProvided:
        value = _handle_SchemaNotProvided(field_name, field, value)
    except WrongType:
        value = _handle_WrongType(field_name, field, value)
        # Lets try again with the adapted value
        return validate_field_value(self, field_name, field, value)
    except WrongContainedType:
        value = _handle_WrongContainedType(field_name, field, value)

    if (field.readonly
            and field.query(self) is None
            and field.queryTaggedValue('_ext_allow_initial_set')):
        if value is not None:
            # First time through we get to set it, but we must bypass
            # the field
            _do_set = SetattrSet(self, str(field_name), value)
        else:
            _do_set = noop
    else:
        _do_set = FieldSet(self, field, value)

    return _do_set


def validate_named_field_value(self, iface, field_name, value):
    """
    Given a :class:`zope.interface.Interface` and the name of one of its attributes,
    validate that the given ``value`` is appropriate to set. See :func:`validate_field_value`
    for details.

    :param string field_name: The name of a field contained in
        `iface`. May name a regular :class:`zope.interface.Attribute`,
        or a :class:`zope.schema.interfaces.IField`; if the latter,
        extra validation will be possible.

    :return: A callable of no arguments to call to actually set the value.
    """
    field = iface[field_name]
    if IField_providedBy(field):
        return validate_field_value(self, field_name, field, value)

    return SetattrSet(self, field_name, value)


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._fields')

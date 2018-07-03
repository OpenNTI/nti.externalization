# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for validating and setting individual fields
(attributes) of an object.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# stdlib imports
import sys

from six import text_type
from six import reraise

from zope.interface import implementedBy

from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import SchemaNotProvided
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import WrongContainedType
from zope.schema.interfaces import WrongType

IField_providedBy = IField.providedBy

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
        self.field = field
        self.value = value

    def __call__(self):
        self.field.set(self.ext_self, self.value)

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
    # XXX: Simplify this
    # pylint:disable=too-many-branches
    __traceback_info__ = field_name, value
    field = field.bind(self)
    try:
        if isinstance(value, text_type) and IFromUnicode.providedBy(field):
            value = field.fromUnicode(value)  # implies validation
        else:
            field.validate(value)
    except SchemaNotProvided as e:
        # The object doesn't implement the required interface.
        # Can we adapt the provided object to the desired interface?
        # First, capture the details so we can reraise if needed
        exc_info = sys.exc_info()
        if not e.args:  # zope.schema doesn't fill in the details, which sucks
            e.args = (field_name, field.schema)

        try:
            value = field.schema(value)
            field.validate(value)
        except (LookupError, TypeError, ValidationError, AttributeError):
            # Nope. TypeError (or AttrError - Variant) means we couldn't adapt,
            # and a validation error means we could adapt, but it still wasn't
            # right. Raise the original SchemaValidationError.
            reraise(*exc_info)
        finally:
            del exc_info
    except WrongType as e:
        # Like SchemaNotProvided, but for a primitive type,
        # most commonly a date
        # Can we adapt?
        if len(e.args) != 3: # pragma: no cover
            raise
        exc_info = sys.exc_info()
        exp_type = e.args[1]
        # If the type unambiguously implements an interface (one interface)
        # that's our target. IDate does this
        if len(list(implementedBy(exp_type))) != 1:
            try:
                raise # pylint:disable=misplaced-bare-raise
            finally:
                del exc_info
        schema = list(implementedBy(exp_type))[0]
        try:
            value = schema(value)
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
        finally:
            del exc_info

        # Lets try again with the adapted value
        return validate_field_value(self, field_name, field, value)

    except WrongContainedType as e:
        # We failed to set a sequence. This would be of simple (non externalized)
        # types.
        # Try to adapt each value to what the sequence wants, just as above,
        # if the error is one that may be solved via simple adaptation
        # TODO: This is also thrown from IObject fields when validating the
        # fields of the object
        if not e.args or not _all_SchemaNotProvided(e.args[0]):
            raise # pragma: no cover
        exc_info = sys.exc_info()
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
            try:
                raise reraise(*exc_info)
            finally:
                del exc_info


        # Now try to validate the converted value
        try:
            field.validate(value)
        except ValidationError:
            # Nope. TypeError means we couldn't adapt, and a
            # validation error means we could adapt, but it still wasn't
            # right. Raise the original SchemaValidationError.
            raise reraise(*exc_info)
        finally:
            del exc_info

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

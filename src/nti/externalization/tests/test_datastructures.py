#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys
import unittest

from zope import interface
from zope.testing.cleanup import CleanUp

from nti.externalization.tests import ExternalizationLayerTest

from nti.testing.matchers import is_false
from nti.testing.matchers import is_true

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import none

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class,attribute-defined-outside-init,abstract-method
# pylint:disable=no-value-for-parameter,too-many-function-args

class CommonTestMixins(object):

    def _makeOne(self, context=None):
        raise NotImplementedError()

    def test_ext_getattr_default(self):
        io = self._makeOne()
        assert_that(io._ext_getattr(self, 'no_such_attribute', None),
                    is_(none()))

    def test_ext_getattr_no_default(self):
        io = self._makeOne()
        get = io._ext_getattr
        with self.assertRaises(AttributeError):
            get(self, 'no_such_attribute')

    def test_ext_replacement_getattr_default(self):
        io = self._makeOne()
        assert_that(io._ext_replacement_getattr('no_such_attribute', None),
                    is_(none()))

class TestAbstractDynamicObjectIO(CommonTestMixins,
                                  ExternalizationLayerTest):

    def _makeOne(self, context=None):
        from nti.externalization.datastructures import AbstractDynamicObjectIO
        class IO(AbstractDynamicObjectIO):
            _ext_setattr = staticmethod(setattr)
            _ext_getattr = staticmethod(getattr)
            def _ext_all_possible_keys(self):
                return frozenset(self.__dict__)
        return IO()

    def test_ext_dict_key_already_exists(self):
        inst = self._makeOne()
        inst.Creator = inst.creator = "creator"

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({u'Class': 'IO', u'Creator': u'creator'}))


        inst._excluded_out_ivars_ = frozenset()

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({u'Class': 'IO', u'Creator': u'creator', 'creator': 'creator'}))

    def test_ext_dict_primitive_keys_bypass_toExternalObject(self):
        # XXX: We used to monkey-patch datastructures.toExternalObject to
        # make it explode if called, but we can't do that anymore, so this
        # may not be testing what we think it is.
        inst = self._makeOne()
        inst._ext_primitive_out_ivars_ = frozenset({'ivar',})
        inst.ivar = 42

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({'Class': 'IO', 'ivar': 42}))

    def test_ext_dict_sets_parent_on_replacement_value(self):

        class InnerDict(object):
            def toExternalObject(self, **kw):
                return {'key': 42}

        class InnerList(object):
            def toExternalObject(self, **kw):
                return [76]

        inst = self._makeOne()
        inst.ivar = [InnerDict(), InnerList()]
        inst.dict = InnerDict()
        inst.list = InnerList()

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({
                        u'Class': 'IO',
                        'ivar': [{'key': 42}, [76]],
                        'dict': {'key': 42},
                        'list': [76],
                    }))
        assert_that(result['ivar'], has_property('__parent__', inst))
        assert_that(result['ivar'][0], does_not(has_property('__parent__', inst)))
        assert_that(result['ivar'][1], does_not(has_property('__parent__', inst)))

        assert_that(result['dict'], does_not(has_property('__parent__', inst)))
        assert_that(result['list'], does_not(has_property('__parent__', inst)))

    def test_ext_dict_prefer_oid(self):
        merge_from = {'OID': 'oid', 'ID': 'id'}

        inst = self._makeOne()
        result = inst.toExternalDictionary(mergeFrom=merge_from)

        assert_that(result,
                    is_({u'Class': 'IO', 'OID': 'oid', 'ID': 'id'}))

        inst._prefer_oid_ = True
        result = inst.toExternalDictionary(mergeFrom=merge_from)

        assert_that(result,
                    is_({u'Class': 'IO', 'OID': 'oid', 'ID': 'oid'}))

    def test_ext_accept_external_id_false(self):
        inst = self._makeOne()
        assert_that(inst._ext_accept_external_id(self, self), is_false())


    def test_update_takes_external_fields(self):

        parsed = {'ContainerId': 'container',
                  'Creator': 'creator',
                  'ID': 'id'}

        inst = self._makeOne()
        inst.creator = None
        inst.id = None
        inst.containerId = None

        inst.updateFromExternalObject(parsed)

        assert_that(inst, has_property('creator', 'creator'))
        assert_that(inst, has_property('containerId', 'container'))
        # We default to ignoring external id
        assert_that(inst, has_property('id', none()))

        inst._ext_accept_external_id = lambda *args: True
        inst.updateFromExternalObject(parsed)
        assert_that(inst, has_property('id', 'id'))

class TestInterfaceObjectIO(CleanUp,
                            CommonTestMixins,
                            unittest.TestCase):

    def _getTargetClass(self):
        from nti.externalization.datastructures import InterfaceObjectIO
        return InterfaceObjectIO

    def _makeOne(self, context=None, iface_upper_bound=interface.Interface):
        return self._getTargetClass()(context, iface_upper_bound=iface_upper_bound)

    def test_find_primitive_keys_dne(self):
        ext_self = self
        inst = self._makeOne(ext_self, iface_upper_bound=interface.Interface)

        result = inst._ext_find_primitive_keys()
        assert_that(inst, has_property('schema', interface.Interface))
        assert_that(result, is_(set()))

    def test_find_primitive_keys_plain_attribute(self):

        class I(interface.Interface):
            ivar = interface.Attribute("An attribute")

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        possible_keys = inst._ext_all_possible_keys()
        assert_that(possible_keys, is_({'ivar'}))

        result = inst._ext_find_primitive_keys()
        assert_that(result, is_(set()))

    def test_find_primitive_keys_float(self):
        from zope.schema import Float
        class I(interface.Interface):
            ivar = Float() # a plain _type is allowed

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        possible_keys = inst._ext_all_possible_keys()
        assert_that(possible_keys, is_({'ivar'}))

        result = inst._ext_find_primitive_keys()
        assert_that(result, is_({'ivar'}))

    def test_find_primitive_keys_number(self):
        from zope.schema import Float
        class Number(Float):
            _type = (int, float) # a tuple is allowed

        class I(interface.Interface):
            ivar = Number()

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        possible_keys = inst._ext_all_possible_keys()
        assert_that(possible_keys, is_({'ivar'}))

        result = inst._ext_find_primitive_keys()
        assert_that(result, is_({'ivar'}))

    def test_ext_getattr(self):
        ext_self = self
        inst = self._makeOne(ext_self, iface_upper_bound=interface.Interface)

        assert_that(self._makeOne, is_(inst._ext_getattr(ext_self, '_makeOne')))

    def test_ext_accept_external_id_no_field(self):
        # If there is no id field, the value is false

        class I(interface.Interface):
            pass

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        assert_that(inst._ext_accept_external_id(ext_self, None), is_false())

    def test_ext_accept_external_id_no_tagged_value(self):
        # If there is no id field, the value is false

        class I(interface.Interface):
            id = interface.Attribute("An id")

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        assert_that(inst._ext_accept_external_id(ext_self, None), is_false())

    def test_ext_accept_external_id_tagged_value_true(self):
        # If there is no id field, the value is false

        class I(interface.Interface):
            id = interface.Attribute("An id")
            id.setTaggedValue('__external_accept_id__', True)

        @interface.implementer(I)
        class O(object):
            pass

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        assert_that(inst._ext_accept_external_id(ext_self, None), is_true())

    def test_toExternalObject_trivial(self):
        ext_self = self
        inst = self._makeOne(ext_self, iface_upper_bound=interface.Interface)

        result = inst.toExternalObject()
        assert_that(result,
                    is_({'Class': self.__class__.__name__}))

    def test_toExternalObject_external_class_name_iro(self):

        class IBruce(interface.Interface):
            interface.taggedValue('__external_class_name__', 'Batman')

        class IDick(IBruce):
            pass

        @interface.implementer(IBruce)
        class Bruce(object):
            pass

        @interface.implementer(IDick)
        class Dick(object):
            pass


        bruce = Bruce()
        dick = Dick()

        bruce_inst = self._makeOne(bruce, iface_upper_bound=interface.Interface)
        result = bruce_inst.toExternalObject()
        assert_that(result,
                    is_({'Class': 'Batman'}))

        # there's no tagged value, so we get the same thing
        dick_inst = self._makeOne(dick, iface_upper_bound=interface.Interface)
        result = dick_inst.toExternalObject()
        assert_that(result,
                    is_({'Class': 'Batman'}))

        # The actual interface gets passed if it is a callable
        def callable_ext_class_name(iface, ext_self):
            if iface is IDick:
                return 'Boy Wonder'
            return 'Dark Knight'
        IBruce.setTaggedValue('__external_class_name__', callable_ext_class_name)

        result = bruce_inst.toExternalObject()
        assert_that(result,
                    is_({'Class': 'Dark Knight'}))

        result = dick_inst.toExternalObject()
        assert_that(result,
                    is_({'Class': 'Boy Wonder'}))

        # And we can override in IDick
        IDick.setTaggedValue('__external_class_name__', 'Robin')
        result = dick_inst.toExternalObject()
        assert_that(result,
                    is_({'Class': 'Robin'}))

    def test_updateFromExternalObject_trivial(self):
        class O(object):
            pass
        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=interface.Interface)

        # No values, nothing to do.
        inst.updateFromExternalObject({})

    def test_updateFromExternalObject_float(self):
        from zope.schema import Float
        from zope.schema.interfaces import RequiredMissing
        from zope.schema.interfaces import WrongType
        class I(interface.Interface):
            ivar = Float(required=True) # a plain _type is allowed

        @interface.implementer(I)
        class O(object):
            ivar = None

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        # A literal is fine
        inst.updateFromExternalObject({'ivar': 1.0})
        assert_that(ext_self, has_property('ivar', 1.0))

        # A text string is fine
        inst.updateFromExternalObject({'ivar': u'2.0'})
        assert_that(ext_self, has_property('ivar', 2.0))

        # A byte string is NOT fine
        with self.assertRaises(WrongType):
            inst.updateFromExternalObject({'ivar': b'3.0'})

        assert_that(ext_self, has_property('ivar', 2.0))


        # Now a validation error after set
        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        with self.assertRaises(RequiredMissing):
            inst.updateFromExternalObject({})

    def test_updateFromExternalObject_Object(self):
        from zope.schema import Object
        from zope.schema.interfaces import RequiredMissing
        from zope.schema.interfaces import SchemaNotProvided
        class IRequired(interface.Interface):
            pass

        class I(interface.Interface):
            ivar = Object(IRequired)

        @interface.implementer(I)
        class O(object):
            ivar = None

        ext_self = O()
        inst = self._makeOne(ext_self, iface_upper_bound=I)

        with self.assertRaises(RequiredMissing):
            inst.updateFromExternalObject({})

        with self.assertRaises(SchemaNotProvided):
            inst.updateFromExternalObject({'ivar': self})

        @interface.implementer(IRequired)
        class Required(object):
            pass

        inst.updateFromExternalObject({'ivar': Required()})

    def test_find_factory_for_named_value(self):
        from zope import component
        from zope.schema import Int
        class I(interface.Interface):
            field = Int()

        @interface.implementer(I)
        class O(object):
            pass

        inst = self._makeOne(O(), iface_upper_bound=I)

        # Key not in schema: not an error (XXX should it be?)
        assert_that(inst.find_factory_for_named_value('missing', {}, component),
                    is_(none()))

        # object that's not-string: not an error (XXX: should it be? we don't
        # test for 'callable' for performance)
        I['field'].setTaggedValue('__external_factory__', self)

        assert_that(inst.find_factory_for_named_value('field', {}, component),
                    is_(self))

        # string object is looked up as a utility
        I['field'].setTaggedValue('__external_factory__', 'some factory')
        with self.assertRaises(component.ComponentLookupError):
            inst.find_factory_for_named_value('field', {}, component)


class TestModuleScopedInterfaceObjectIO(TestInterfaceObjectIO):

    def _getTargetClass(self):
        from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO
        class IO(ModuleScopedInterfaceObjectIO):
            _ext_search_module = sys.modules[__name__]
        return IO

    def test_finding_linear_interface(self):

        class IRoot(interface.Interface):
            pass

        class IChild(IRoot):
            pass

        class IGrandChild(IChild):
            pass

        class ISister(IRoot):
            pass

        @interface.implementer(IGrandChild, ISister)
        class Inconsistent(object):
            pass

        mod = sys.modules[__name__]

        class IO(self._getTargetClass()):
            _ext_search_module = mod

        with self.assertRaises(TypeError):
            IO(Inconsistent())

        @interface.implementer(ISister)
        class Sister(object):
            pass

        @interface.implementer(IGrandChild)
        class InconsistentGrandChild(Sister):
            pass

        with self.assertRaises(TypeError):
            IO(InconsistentGrandChild())

        @interface.implementer(IGrandChild)
        class Consistent(object):
            pass

        io = IO(Consistent())
        assert_that(io, has_property('_iface', IGrandChild))


class TestExternalizableInstanceDict(CommonTestMixins,
                                     unittest.TestCase):

    def _makeOne(self, context=None):
        from nti.externalization.datastructures import ExternalizableInstanceDict
        class FUT(ExternalizableInstanceDict):
            def _ext_replacement(self):
                return context

        return FUT()

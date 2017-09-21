#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys
import unittest

import fudge
from zope import interface

from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO
from nti.externalization.tests import ExternalizationLayerTest

from nti.testing.matchers import is_false

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import none

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class,attribute-defined-outside-init,abstract-method


class TestModuleScopedInterfaceObjectIO(unittest.TestCase):

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

        class IO(ModuleScopedInterfaceObjectIO):
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


class TestAbstractDynamicObjectIO(ExternalizationLayerTest):

    def _makeOne(self):
        from nti.externalization.datastructures import AbstractDynamicObjectIO
        class IO(AbstractDynamicObjectIO):
            _ext_setattr = staticmethod(setattr)
            _ext_getattr = staticmethod(getattr)
            def _ext_all_possible_keys(self):
                return self.__dict__
        return IO()

    def test_ext_dict_key_already_exists(self):
        inst = self._makeOne()
        inst.Creator = inst.creator = "creator"

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({u'Class': 'IO', u'Creator': u'creator'}))


        inst._excluded_out_ivars_ = ()

        result = inst.toExternalDictionary()
        assert_that(result,
                    is_({u'Class': 'IO', u'Creator': u'creator', 'creator': 'creator'}))

    @fudge.patch('nti.externalization.datastructures.toExternalObject')
    def test_ext_dict_primitive_keys_bypass_toExternalObject(self, toExternalObject):
        # leave the toExternalObject alone, if it is called it will
        # raise an error.
        inst = self._makeOne()
        inst._ext_primitive_out_ivars_ = ('ivar',)
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

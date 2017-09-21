#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys
import unittest

from zope import interface
from zope.interface.common.idatetime import IDate
from zope.testing.cleanup import CleanUp

from nti.externalization.tests import ExternalizationLayerTest
from nti.schema.interfaces import InvalidValue

from .. import internalization as INT

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import none
from hamcrest import raises

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class


class TestDate(ExternalizationLayerTest):

    def test_exception(self):
        assert_that(calling(IDate).with_args('xx'), raises(InvalidValue))


class TestEvents(CleanUp,
                 unittest.TestCase):

    def _doIt(self, *args, **kwargs):
        from nti.externalization.internalization import notifyModified
        from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

        event = notifyModified(*args, **kwargs)
        self.assertIsInstance(event, ObjectModifiedFromExternalEvent)
        return event

    def test_notify_event_kwargs(self):
        event = self._doIt(self, {'external': True}, a_key=42)
        self.assertEqual(event.kwargs, {'a_key': 42})
        assert_that(event, has_property('external_value', {'external': True}))

    def test_attributes(self):
        class IFoo(interface.Interface):
            attr_foo_1 = interface.Attribute("An attribute")
            attr_foo_2 = interface.Attribute("An attribute")

        class IBar(interface.Interface):
            attr_bar_1 = interface.Attribute("An attribute")
            attr_bar_2 = interface.Attribute("An attribute")
            attr_foo_1 = interface.Attribute("An attribute")

        @interface.implementer(IFoo, IBar)
        class FooBar(object):
            pass

        obj = FooBar()
        keys = {'attr_foo_1', 'attr_bar_1', 'attr_bar_2', 'no_iface_attr'}

        event = self._doIt(obj, {}, external_keys=keys)

        attributes = sorted(event.descriptions,
                            key=lambda attrs: attrs.interface)
        assert_that(attributes, has_length(3))
        assert_that(attributes[0].interface, is_(IBar))
        assert_that(attributes[0].attributes, is_(('attr_bar_1', 'attr_bar_2',)))

        assert_that(attributes[1].interface, is_(IFoo))
        assert_that(attributes[1].attributes, is_(('attr_foo_1',)))

        assert_that(attributes[2].interface, is_(none()))
        assert_that(attributes[2].attributes, is_(('no_iface_attr',)))


class TestFunctions(CleanUp,
                    unittest.TestCase):


    def test_search_for_factory_no_type(self):
        assert_that(INT._search_for_external_factory(''), is_(none()))

    def test_search_for_factory_updates_search_set(self):
        INT.LEGACY_FACTORY_SEARCH_MODULES.add(__name__)
        assert_that(INT._search_for_external_factory('testfunctionss'), is_(none()))
        assert_that(sys.modules[__name__], is_in(INT.LEGACY_FACTORY_SEARCH_MODULES))
        assert_that(__name__, is_not(is_in(INT.LEGACY_FACTORY_SEARCH_MODULES)))

        TestFunctions.__external_can_create__ = True
        try:
            assert_that(INT._search_for_external_factory('testfunctionss'), TestFunctions)
        finally:
            del TestFunctions.__external_can_create__

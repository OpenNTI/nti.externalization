# -*- coding: utf-8 -*-
"""
Tests for reading data into objects from external data *not* following
the conventions of this package, e.g., missing Class and MimeType values.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint:disable=inherit-non-class

import unittest

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property as has_attr

from zope import interface
from zope import component

from zope.schema import Object
from zope.schema import Int
from zope.schema import List

from zope.testing.cleanup import CleanUp

from nti.externalization.internalization import update_from_external_object
from nti.externalization.datastructures import InterfaceObjectIO


class TestExternals(CleanUp,
                    unittest.TestCase):

    def test_single_object_field_names_match_non_primitive(self):
        class INestedThing(interface.Interface):
            value = Int(title=u"An integer")

        class IRoot(interface.Interface):
            field = Object(INestedThing)


        class IO(InterfaceObjectIO):
            _ext_iface_upper_bound = IRoot
        component.provideAdapter(IO, adapts=(IRoot,))

        class IO2(InterfaceObjectIO):
            _ext_iface_upper_bound = INestedThing

        component.provideAdapter(IO2, adapts=(INestedThing,))

        @interface.implementer(IRoot)
        class Root(object):

            def __init__(self):
                self.field = None

        @interface.implementer(INestedThing)
        class NestedThing(object):

            def __init__(self):
                self.value = -1

        IRoot['field'].setTaggedValue('__external_factory__', NestedThing)

        external = {'field': {'value': 42}}

        root = Root()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(NestedThing)))
        assert_that(root.field, has_attr('value', 42))


    def test_sequence_object_field_names_match_non_primitive(self):
        class INestedThing(interface.Interface):
            value = Int(title=u"An integer")

        class IRoot(interface.Interface):
            field = List(Object(INestedThing))


        class IO(InterfaceObjectIO):
            _ext_iface_upper_bound = IRoot
        component.provideAdapter(IO, adapts=(IRoot,))

        class IO2(InterfaceObjectIO):
            _ext_iface_upper_bound = INestedThing

        component.provideAdapter(IO2, adapts=(INestedThing,))

        @interface.implementer(IRoot)
        class Root(object):

            def __init__(self):
                self.field = ()

        @interface.implementer(INestedThing)
        class NestedThing(object):

            def __init__(self):
                self.value = -1

        IRoot['field'].setTaggedValue('__external_factory__', NestedThing)

        external = {'field': [{'value': 42}, {'value': 2018}]}

        root = Root()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(list)))
        assert_that(root.field[0], has_attr('value', 42))
        assert_that(root.field[1], has_attr('value', 2018))

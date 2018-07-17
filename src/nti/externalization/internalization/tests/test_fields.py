# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

from zope import interface
from zope.component import eventtesting


from zope.schema.interfaces import IBeforeObjectAssignedEvent
from zope.schema.interfaces import IFieldUpdatedEvent
from zope.schema.interfaces import SchemaNotProvided
from zope.schema import Object
from zope.schema.fieldproperty import createFieldProperties

from zope.testing.cleanup import CleanUp

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_property as has_attr
from hamcrest import is_
from hamcrest import same_instance

from nti.externalization.internalization.fields import validate_named_field_value

# pylint:disable=inherit-non-class

class IThing(interface.Interface):
    pass

class IBar(interface.Interface):

    thing = Object(IThing)

@interface.implementer(IThing)
class Thing(object):
    pass

@interface.implementer(IBar)
class Bar(object):
    createFieldProperties(IBar)

class TestValidateFieldValueEvents(CleanUp,
                                   unittest.TestCase):

    def setUp(self):
        eventtesting.setUp()


    def test_before_object_assigned_event_fired_valid_value(self):

        thing = Thing()
        root = Bar()

        validate_named_field_value(root, IBar, 'thing', thing)()

        events = eventtesting.getEvents(IBeforeObjectAssignedEvent)
        assert_that(events, has_length(1))
        assert_that(events[0], has_attr('object', is_(same_instance(thing))))

        events = eventtesting.getEvents(IFieldUpdatedEvent)
        assert_that(events, has_length(1))


    def test_before_object_assigned_event_fired_invalid_value_fixed(self):
        thing = Thing()
        root = Bar()

        class NotThing(object):
            def __conform__(self, iface):
                return thing if iface is IThing else None


        validate_named_field_value(root, IBar, 'thing', NotThing())()

        events = eventtesting.getEvents(IBeforeObjectAssignedEvent)
        assert_that(events, has_length(1))
        assert_that(events[0], has_attr('object', is_(same_instance(thing))))

        events = eventtesting.getEvents(IFieldUpdatedEvent)
        assert_that(events, has_length(1))


    def test_before_object_assigned_event_not_fired_invalid_value(self):

        with self.assertRaises(SchemaNotProvided):
            validate_named_field_value(Bar(), IBar, 'thing', object())

        events = eventtesting.getEvents(IBeforeObjectAssignedEvent)
        assert_that(events, has_length(0))

        events = eventtesting.getEvents(IFieldUpdatedEvent)
        assert_that(events, has_length(0))

# -*- coding: utf-8 -*-
"""
Tests for updater.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from zope import interface
from zope import component

from zope.testing.cleanup import CleanUp

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import has_length
from hamcrest import is_
from hamcrest import same_instance

from nti.externalization import interfaces

from nti.externalization.internalization import updater

class CreateCount(object):
    created = 0
    def __init__(self, context):
        type(self).created += 1

@interface.implementer(interfaces.IInternalObjectIOFinder)
@component.adapter(object)
class NEOFF(CreateCount):
    created = 0
    found = 0

    def find_factory_for_named_value(self, *args):
        NEOFF.found += 1

class DomainObject(object):
    pass

@interface.implementer(interfaces.IInternalObjectUpdater)
@component.adapter(DomainObject)
class CorrectUpdater(CreateCount):
    created = 0
    updated = 0
    def updateFromExternalObject(self, *args):
        CorrectUpdater.updated += 1


@interface.implementer(interfaces.IExternalizedObjectFactoryFinder)
@component.adapter(object)
class WorkingExternalizedObjectFactoryFinder(object):

    def __init__(self, context):
        pass

    def find_factory(self, ext):
        return DomainObject

class TestUpdater(CleanUp,
                  unittest.TestCase):

    def setUp(self):
        from zope import event

        self.events = events = []
        event.subscribers.append(events.append)


    def tearDown(self):
        from zope import event
        CreateCount.created = 0
        NEOFF.created = NEOFF.found = 0
        CorrectUpdater.created = CorrectUpdater.updated = 0
        event.subscribers.remove(self.events.append)

        registry = component.getSiteManager()
        registry.unregisterAdapter(CorrectUpdater)
        registry.unregisterAdapter(NEOFF)
        registry.unregisterAdapter(WorkingExternalizedObjectFactoryFinder)

    def test_less_specific_named_externalizer_doesnt_trump_specific_updater(self):
        component.provideAdapter(CorrectUpdater)
        component.provideAdapter(NEOFF)

        ext = {'a': object()}
        domain = DomainObject()
        updater.update_from_external_object(domain, ext, require_updater=True)

        assert_that(NEOFF, has_property('created', 1))
        assert_that(NEOFF, has_property('found', 1))
        assert_that(CorrectUpdater, has_property('created', 1))
        assert_that(CorrectUpdater, has_property('updated', 1))

    def test_will_update_event(self):
        component.provideAdapter(CorrectUpdater)
        events = self.events

        ext = {'a': object()}
        domain = DomainObject()

        updater.update_from_external_object(domain, ext, require_updater=True)

        assert_that(events, has_length(2))
        assert_that(events[0], is_(interfaces.ObjectWillUpdateFromExternalEvent))
        will = events[0]
        assert_that(will.root, is_(same_instance(domain)))
        assert_that(will.object, is_(same_instance(domain)))
        assert_that(will.external_value, is_(ext))

        assert_that(events[1], is_(interfaces.ObjectModifiedFromExternalEvent))

    def test_will_update_event_sequence(self):
        component.provideAdapter(CorrectUpdater)
        component.provideAdapter(WorkingExternalizedObjectFactoryFinder)

        events = self.events

        ext = [{'MimeType': 'abc'}, {'MimeType': 'abc'}]
        orig_ext = list(ext)
        domain = [DomainObject(), DomainObject()]

        updater.update_from_external_object(domain, ext, require_updater=True)

        assert_that(events, has_length(4))
        assert_that(events[0], is_(interfaces.ObjectWillUpdateFromExternalEvent))
        assert_that(events[2], is_(interfaces.ObjectWillUpdateFromExternalEvent))
        will = events[0]
        assert_that(will.root, is_(domain))
        assert_that(will.external_value, is_(orig_ext[0]))

        assert_that(events[1], is_(interfaces.ObjectModifiedFromExternalEvent))
        assert_that(events[3], is_(interfaces.ObjectModifiedFromExternalEvent))

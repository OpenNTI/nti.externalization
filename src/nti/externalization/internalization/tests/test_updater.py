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

from nti.externalization import interfaces

from nti.externalization.internalization import updater

class TestUpdater(CleanUp,
                  unittest.TestCase):

    def test_less_specific_named_externalizer_doesnt_trump_specific_updater(self):

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
                return None

        class DomainObject(object):
            pass

        @interface.implementer(interfaces.IInternalObjectUpdater)
        @component.adapter(DomainObject)
        class CorrectUpdater(CreateCount):
            created = 0
            updated = 0
            def updateFromExternalObject(self, *args):
                CorrectUpdater.updated += 1

        component.provideAdapter(CorrectUpdater)
        component.provideAdapter(NEOFF)

        ext = {'a': object()}
        domain = DomainObject()
        updater.update_from_external_object(domain, ext, require_updater=True)

        assert_that(NEOFF, has_property('created', 1))
        assert_that(NEOFF, has_property('found', 1))
        assert_that(CorrectUpdater, has_property('created', 1))
        assert_that(CorrectUpdater, has_property('updated', 1))

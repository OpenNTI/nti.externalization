# -*- coding: utf-8 -*-
"""
Tests for objects used in the benchmark process.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from . import ExternalizationLayerTest

class TestBenchmarkObjects(ExternalizationLayerTest):

    def test_user_profile(self):

        from nti.externalization.tests.benchmarks.objects import Address
        from nti.externalization.tests.benchmarks.objects import UserProfile

        home_address = Address(
            full_name=u'Steve Jobs',
            street_address_1=u'1313 Mockingbird Lane',
            city=u'Salem',
            state=u'MA',
            postal_code=u'6666',
            country=u'USA',
        )

        work_address = Address(
            full_name=u'Apple',
            street_address_1=u'1 Infinite Loop',
            city=u'Cupertino',
            state=u'CA',
            postal_code=u'55555',
            country=u'USA',
        )

        user_profile = UserProfile(
            addresses={u'home': home_address, u'work': work_address},
            phones={u'home': u'405-555-1212', u'work': u'405-555-2323'},
            contact_emails={u'home': u'steve.jobs@gmail.com', u'work': u'steve@apple.com'},
            avatarURL='http://apple.com/steve.png',
            backgroundURL='https://apple.com/bg.jpeg',
            alias=u'Steve',
            realname=u'Steve Jobs',
        )

        mt = getattr(UserProfile, 'mimeType')
        assert_that(mt, is_('application/vnd.nextthought.benchmarks.userprofile'))

        ext = toExternalObject(user_profile)
        assert_that(ext, has_key(StandardExternalFields.MIMETYPE))
        assert_that(ext['addresses'], has_key('home'))
        assert_that(ext['addresses']['home'], has_key("city"))


        addr = update_from_external_object(Address(), toExternalObject(home_address))
        assert_that(addr, is_(home_address))
        prof2 = update_from_external_object(UserProfile(), toExternalObject(user_profile))
        assert_that(prof2, is_(user_profile))

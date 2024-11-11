# -*- coding: utf-8 -*-
"""
Tests for objects used in the benchmark process.

"""

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
            full_name='Steve Jobs',
            street_address_1='1313 Mockingbird Lane',
            city='Salem',
            state='MA',
            postal_code='6666',
            country='USA',
        )

        work_address = Address(
            full_name='Apple',
            street_address_1='1 Infinite Loop',
            city='Cupertino',
            state='CA',
            postal_code='55555',
            country='USA',
        )

        user_profile = UserProfile(
            addresses={'home': home_address, 'work': work_address},
            phones={'home': '405-555-1212', 'work': '405-555-2323'},
            contact_emails={'home': 'steve.jobs@gmail.com', 'work': 'steve@apple.com'},
            avatarURL='http://apple.com/steve.png',
            backgroundURL='https://apple.com/bg.jpeg',
            alias='Steve',
            realname='Steve Jobs',
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

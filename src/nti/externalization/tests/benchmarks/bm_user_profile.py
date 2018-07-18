# -*- coding: utf-8 -*-
"""
Benchmarks a realistic user profile object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

import perf


from zope.configuration import xmlconfig

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import update_from_external_object

import nti.externalization.tests.benchmarks

from nti.externalization.tests.benchmarks.objects import Address
from nti.externalization.tests.benchmarks.objects import Addresses
from nti.externalization.tests.benchmarks.objects import UserProfile

from nti.externalization.tests.benchmarks.bm_simple_iface import (
    INNER_LOOPS,
    to_external_object_time_func,
    update_from_external_object_time_func,
    profile
)

logger = __import__('logging').getLogger(__name__)


def main(runner=None):

    xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)

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
        addresses=Addresses(home=home_address, work=work_address),
        phones={u'home': u'405-555-1212', u'work': u'405-555-2323'},
        contact_emails={u'home': u'steve.jobs@gmail.com', u'work': u'steve@apple.com'},
        avatarURL='http://apple.com/steve.png',
        backgroundURL='https://apple.com/bg.jpeg',
        alias=u'Steve',
        realname=u'Steve Jobs',
    )


    if '--profile' in sys.argv:
        profile(100, user_profile)
        return

    mt = getattr(user_profile, 'mimeType')
    assert mt == 'application/vnd.nextthought.benchmarks.userprofile', mt

    ext = toExternalObject(user_profile)
    assert StandardExternalFields.MIMETYPE in ext

    addr = update_from_external_object(Address(), toExternalObject(home_address),
                                       require_updater=True)
    assert addr == home_address
    prof2 = update_from_external_object(UserProfile(), toExternalObject(user_profile),
                                        require_updater=True)
    assert prof2 == user_profile

    runner = runner or perf.Runner()
    runner.bench_time_func(__name__ + ": toExternalObject",
                           to_external_object_time_func,
                           user_profile,
                           inner_loops=INNER_LOOPS)


    runner.bench_time_func(__name__ + ": fromExternalObject",
                           update_from_external_object_time_func,
                           ext,
                           inner_loops=INNER_LOOPS)

if __name__ == '__main__':
    main()

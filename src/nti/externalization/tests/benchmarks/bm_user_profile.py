# -*- coding: utf-8 -*-
"""
Benchmarks a realistic user profile object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

import pyperf as perf


from zope.configuration import xmlconfig

from nti.externalization.externalization import toExternalObject

import nti.externalization.tests.benchmarks

from nti.externalization.tests.benchmarks.objects import Address
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


    if '--profile' in sys.argv:
        profile(100, user_profile)
        return

    ext = toExternalObject(user_profile)

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

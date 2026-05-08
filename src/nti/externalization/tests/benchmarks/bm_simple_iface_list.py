# -*- coding: utf-8 -*-
"""
Extends bm_simple_iface to add a list.

"""

import sys

from zope.configuration import xmlconfig

import nti.externalization.tests.benchmarks
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.tests.benchmarks.bm_simple_iface import INNER_LOOPS
from nti.externalization.tests.benchmarks.bm_simple_iface import profile
from nti.externalization.tests.benchmarks.bm_simple_iface import to_external_object_time_func
from nti.externalization.tests.benchmarks.bm_simple_iface import \
    update_from_external_object_time_func
from nti.externalization.tests.benchmarks.bm_simple_iface import vmprofile
from nti.externalization.tests.benchmarks.objects import DerivedWithOneTextField
from nti.externalization.tests.benchmarks.objects import HasListOfDerived

import pyperf as perf


def main(runner=None):

    xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)

    obj = HasListOfDerived()
    obj.the_objects = [DerivedWithOneTextField(text="This is some text " + str(i))
                       for i in range(10)]

    if '--profile' in sys.argv:
        profile(100, obj)
        return

    if '--vmprofile' in sys.argv:
        vmprofile(100, obj)
        return

    mt = getattr(obj, 'mimeType')
    assert mt == 'application/vnd.nextthought.benchmarks.haslistofderived', mt

    runner = runner or perf.Runner()
    runner.bench_time_func(__name__ + ": toExternalObject",
                           to_external_object_time_func,
                           obj,
                           inner_loops=INNER_LOOPS)

    ext = toExternalObject(obj)
    assert StandardExternalFields.MIMETYPE in ext


    runner.bench_time_func(__name__ + ": fromExternalObject",
                           update_from_external_object_time_func,
                           ext,
                           inner_loops=INNER_LOOPS)

if __name__ == '__main__':
    main()

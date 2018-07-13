# -*- coding: utf-8 -*-
"""
Benchmark for a simple registered autopackage IFace with
a single text field.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import sys

import perf
from perf import perf_counter

from zope.configuration import xmlconfig

from nti.externalization.representation import JsonRepresenter
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import default_externalized_object_factory_finder
from nti.externalization.internalization import update_from_external_object

import nti.externalization.tests.benchmarks
from nti.externalization.tests.benchmarks.objects import DerivedWithOneTextField

INNER_LOOPS = 100

def to_external_object_time_func(loops, obj):
    begin = perf_counter()
    for _ in range(loops):
        for _ in range(INNER_LOOPS):
            toExternalObject(obj)
    end = perf_counter()
    return end - begin

def find_factory_time_func(loops, ext):
    begin = perf_counter()
    for _ in range(loops):
        for _ in range(INNER_LOOPS):
            default_externalized_object_factory_finder(ext)()
    end = perf_counter()
    return end - begin

def update_from_external_object_time_func(loops, ext):
    factory = default_externalized_object_factory_finder(ext)
    # Updating *may* modify the object in place, so we need to
    # make deep copies of it.
    rep = JsonRepresenter()
    json = rep.dump(ext)
    exts = [rep.load(json) for x in range(loops * INNER_LOOPS)]
    begin = perf_counter()
    for x in exts:
        obj = factory()
        update_from_external_object(obj, x)
    end = perf_counter()
    return end - begin


def profile(loops=1000, obj=None):
    from cProfile import Profile
    import pstats

    if obj is None:
        obj = DerivedWithOneTextField()
        obj.text = u'This is some text'

    ext = toExternalObject(obj)

    for func, arg in (
            (to_external_object_time_func, obj),
            (find_factory_time_func, ext),
            (update_from_external_object_time_func, ext),
    ):

        prof = Profile()
        prof.enable()
        func(loops, arg)
        prof.disable()
        stats = pstats.Stats(prof)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        print("Profile of", func)
        stats.print_stats(20)

def vmprofile(loops=1000, obj=None):
    import vmprof

    if obj is None:
        obj = DerivedWithOneTextField()
        obj.text = u'This is some text'

    ext = toExternalObject(obj)

    for func, arg in (
            (to_external_object_time_func, obj),
            (find_factory_time_func, ext),
            # This one often segfaults if we use Cython somewhere in the
            # guts of libunwind.
            (update_from_external_object_time_func, ext),
    ):
        with open('benchmark_results/' + func.__name__ + '.vmprof', 'w+b') as f:
            print("Begin", func)
            vmprof.enable(f.fileno())
            func(loops, arg)
            vmprof.disable()
            print("End", func)


def main(runner=None):

    xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)

    if '--profile' in sys.argv:
        profile()
        return

    obj = DerivedWithOneTextField()
    obj.text = u"This is some text"

    assert obj.mimeType == 'application/vnd.nextthought.benchmarks.derivedwithonetextfield'

    runner = runner or perf.Runner()
    runner.bench_time_func(__name__ + ": toExternalObject",
                           to_external_object_time_func,
                           obj,
                           inner_loops=INNER_LOOPS)

    ext = toExternalObject(obj)
    assert StandardExternalFields.MIMETYPE in ext

    runner.bench_time_func(__name__ + ': find factory',
                           find_factory_time_func,
                           ext,
                           inner_loops=INNER_LOOPS)

    runner.bench_time_func(__name__ + ": fromExternalObject",
                           update_from_external_object_time_func,
                           ext,
                           inner_loops=INNER_LOOPS)



if __name__ == '__main__':
    main()

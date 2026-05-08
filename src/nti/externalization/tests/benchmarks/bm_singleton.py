# -*- coding: utf-8 -*-
"""
Benchmark for creating singleton objects.

"""

from nti.externalization.singleton import Singleton

import pyperf as perf


# These are defined to have __slots__ = ()
class SingletonSubclass(Singleton):
    pass


class ObjectSubclass(object):
    __slots__ = ()
    def __init__(self, _context=None, _request=None):
        pass


def main(runner=None):

    runner = runner or perf.Runner()
    runner.bench_func('Construct Singleton', SingletonSubclass)

    runner.bench_func('Construct non-Singleton', ObjectSubclass)

    runner.bench_func('Construct Singleton with args',
                      SingletonSubclass, 'context', 'request')

    runner.bench_func("Construct non-Singleton with args",
                      ObjectSubclass, 'context', 'request')


if __name__ == '__main__':
    main()

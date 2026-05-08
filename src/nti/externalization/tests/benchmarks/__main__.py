# -*- coding: utf-8 -*-
"""
Main file to run when the package is specified. Primary CLI.

"""

import glob
import os
import os.path

from zope.dottedname import resolve as dottedname

import pyperf as perf

here = os.path.dirname(__file__)

def find_benchmarks():
    modules = []
    fnames = [os.path.basename(f)[:-3]
              for f
              in glob.glob(os.path.join(here, 'bm_*.py'))]

    modules = [dottedname.resolve('nti.externalization.tests.benchmarks.' + f)
               for f in fnames]
    return modules

def main():

    runner = perf.Runner()
    for mod in find_benchmarks():
        mod.main(runner)


if __name__ == '__main__':
    main()

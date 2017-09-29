# -*- coding: utf-8 -*-
"""
Main file to run when the package is specified. Primary CLI.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import glob
import os
import os.path

import perf
from zope.dottedname import resolve as dottedname

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

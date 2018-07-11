# -*- coding: utf-8 -*-
"""
Benchmark for a simple registered Class factory object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import warnings

import perf
from zope.configuration import xmlconfig

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import default_externalized_object_factory_finder
from nti.externalization.internalization import update_from_external_object
import nti.externalization.tests.benchmarks
from nti.externalization.tests.benchmarks.objects import SimplestPossibleObject

# pylint:disable=arguments-differ

class NoArgs(SimplestPossibleObject):

    def updateFromExternalObject(self, external_object):
        self.__dict__.update(external_object)

class ContextArg(SimplestPossibleObject):

    def updateFromExternalObject(self, external_object, context=None):
        self.__dict__.update(external_object)

class DSArg(SimplestPossibleObject):

    def updateFromExternalObject(self, external_object, dataserver=None):
        self.__dict__.update(external_object)

def main(runner=None):

    xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)

    obj = SimplestPossibleObject()

    def func():
        toExternalObject(obj)

    runner = runner or perf.Runner()
    runner.bench_func(__name__ + ": toExternalObject", func)

    ext = toExternalObject(obj)
    ext.pop(StandardExternalFields.MIMETYPE, None)

    def from_():
        obj = default_externalized_object_factory_finder(ext)()
        update_from_external_object(obj, ext)

    runner.bench_func(__name__ + ": fromExternalObject", from_)


    def no_args():
        obj = NoArgs()
        update_from_external_object(obj, ext)

    def context_arg():
        obj = ContextArg()
        update_from_external_object(obj, ext)

    def ds_arg():
        obj = DSArg()
        update_from_external_object(obj, ext)


    runner.bench_func(__name__ + ": fromExternalObject (no args)", no_args)

    runner.bench_func(__name__ + ": fromExternalObject (context arg)", context_arg)

    warnings.simplefilter('ignore')
    runner.bench_func(__name__ + ": fromExternalObject (ds arg)", ds_arg)




if __name__ == '__main__':
    main()

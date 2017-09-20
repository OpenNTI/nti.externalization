#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys

from zope import interface

from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO
from nti.externalization.tests import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import has_property

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class TestDatastructures(ExternalizationLayerTest):

    def test_finding_linear_interface(self):

        class IRoot(interface.Interface):
            pass

        class IChild(IRoot):
            pass

        class IGrandChild(IChild):
            pass

        class ISister(IRoot):
            pass

        @interface.implementer(IGrandChild, ISister)
        class Inconsistent(object):
            pass

        mod = sys.modules[__name__]

        class IO(ModuleScopedInterfaceObjectIO):
            _ext_search_module = mod

        with self.assertRaises(TypeError):
            IO(Inconsistent())

        @interface.implementer(ISister)
        class Sister(object):
            pass

        @interface.implementer(IGrandChild)
        class InconsistentGrandChild(Sister):
            pass

        with self.assertRaises(TypeError):
            IO(InconsistentGrandChild())

        @interface.implementer(IGrandChild)
        class Consistent(object):
            pass

        io = IO(Consistent())
        assert_that(io, has_property('_iface', IGrandChild))

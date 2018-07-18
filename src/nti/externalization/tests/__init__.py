#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

import zope.testing.cleanup

import nti.testing.base
from nti.testing.layers import ConfiguringLayerMixin
from nti.testing.layers import ZopeComponentLayer

# BWC exports
from nti.externalization.testing import Externalizes
from nti.externalization.testing import externalizes
from nti.externalization.testing import assert_does_not_pickle
Externalizes = Externalizes
externalizes = externalizes
assert_does_not_pickle = assert_does_not_pickle


class ConfiguringTestBase(nti.testing.base.ConfiguringTestBase):
    set_up_packages = ('nti.externalization',)


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 ConfiguringLayerMixin):

    set_up_packages = (
        'nti.externalization',
        'nti.externalization.tests.benchmarks',
    )

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


class ExternalizationLayerTest(unittest.TestCase):
    layer = SharedConfiguringTestLayer

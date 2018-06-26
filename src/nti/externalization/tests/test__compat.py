# -*- coding: utf-8 -*-
"""
Tests for _compat.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function



# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

from nti.externalization import _compat as FUT

class TestFuncs(unittest.TestCase):

    def test_import_c_accel(self):
        import sys
        old_pp = FUT.PURE_PYTHON
        assert not hasattr(sys, 'import_c_accel')
        sys.import_c_accel = self
        try:
            FUT.PURE_PYTHON = False
            d = {'__name__': 'foo', 'import_c_accel': self}
            FUT.import_c_accel(d, 'sys')
            assert_that(d, has_key('modules'))
            assert_that(d, has_entry('__name__', 'sys'))
            self.assertNotIn('import_c_accel', d)
            FUT.import_c_accel(d, 'sys')
        finally:
            FUT.PURE_PYTHON = old_pp
            del sys.import_c_accel

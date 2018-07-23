# -*- coding: utf-8 -*-
"""
Tests for the sphinx documentation using `Manuel
<https://pythonhosted.org/manuel/>`_.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import doctest
import os.path
import unittest

from zope.testing import renormalizing

import manuel.codeblock
import manuel.doctest
import manuel.testing


def test_suite():
    here = os.path.dirname(__file__)
    while not os.path.exists(os.path.join(here, 'setup.py')):
        here = os.path.join(here, '..')

    here = os.path.abspath(here)
    docs = os.path.join(here, 'docs')

    files_to_test = (
        'basics.rst',
    )

    m = manuel.doctest.Manuel(optionflags=(
        doctest.NORMALIZE_WHITESPACE
        | doctest.ELLIPSIS
        | doctest.IGNORE_EXCEPTION_DETAIL
        | renormalizing.IGNORE_EXCEPTION_MODULE_IN_PYTHON2
    ))
    m += manuel.codeblock.Manuel()

    suite = unittest.TestSuite()
    suite.addTest(
        manuel.testing.TestSuite(
            m,
            *[os.path.join(docs, f) for f in files_to_test]
        )
    )

    return suite

if __name__ == '__main__':
    unittest.main()

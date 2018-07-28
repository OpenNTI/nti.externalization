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
import re
import unittest

from zope.testing import renormalizing
from zope.testing import cleanup

import manuel.capture
import manuel.codeblock
import manuel.doctest
import manuel.ignore
import manuel.testing

checker = renormalizing.RENormalizing([
    # Python 3 bytes add a "b".
    (re.compile("b('.*?')"), r"\1"),
    # and remove the 'u'
    (re.compile("u('.*?')"), r"\1"),
])


def test_suite():
    here = os.path.dirname(__file__)
    while not os.path.exists(os.path.join(here, 'setup.py')):
        here = os.path.join(here, '..')

    here = os.path.abspath(here)
    docs = os.path.join(here, 'docs')

    files_to_test = (
        'basics.rst',
        'externalization.rst',
        'internalization.rst',
    )
    paths = [os.path.join(docs, f) for f in files_to_test]
    kwargs = {'tearDown': lambda _: cleanup.cleanUp}
    m = manuel.ignore.Manuel()
    m += manuel.doctest.Manuel(checker=checker, optionflags=(
        doctest.NORMALIZE_WHITESPACE
        | doctest.ELLIPSIS
        | doctest.IGNORE_EXCEPTION_DETAIL
        | renormalizing.IGNORE_EXCEPTION_MODULE_IN_PYTHON2
    ))
    m += manuel.codeblock.Manuel()
    m += manuel.capture.Manuel()

    suite = unittest.TestSuite()
    suite.addTest(
        manuel.testing.TestSuite(
            m,
            *paths,
            **kwargs
        )
    )

    return suite

if __name__ == '__main__':
    unittest.main()

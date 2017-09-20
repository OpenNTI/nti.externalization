# -*- coding: utf-8 -*-
"""
Support for testing code.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import pickle

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import INonExternalizableReplacement

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import raises
from hamcrest.core.base_matcher import BaseMatcher


class Externalizes(BaseMatcher):

    def __init__(self, matcher=None):
        super(Externalizes, self).__init__()
        self.matcher = matcher

    def _matches(self, item):
        ext_obj = toExternalObject(item)
        result = ext_obj is not None and \
                 not INonExternalizableReplacement.providedBy(ext_obj)
        if result and self.matcher is not None:
            result = self.matcher.matches(ext_obj)

        # For convenience, if the truthy value of ext_obj matches the truthy value of result,
        # return the ext_obj
        return ext_obj if result == bool(ext_obj) else result

    def describe_to(self, description):
        description.append_text('object that can be externalized')
        if self.matcher is not None:
            description.append_text(' to ').append_description_of(self.matcher)

    def describe_mismatch(self, item, mismatch_description):
        ext_obj = toExternalObject(item)
        if ext_obj is None:
            mismatch_description.append_text('externalized to none')
        else:
            text = 'was '
            if INonExternalizableReplacement.providedBy(ext_obj):
                text += 'replaced by '
            mismatch_description.append_text(text).append_description_of(ext_obj)


def externalizes(matcher=None):
    """
    Hamcrest matcher that checks that an object can be externalized.
    You can pass a matcher (such as all_of, any_of, has_entry) to be
    used to check the externalized object.
    """
    return Externalizes(matcher=matcher)


def assert_does_not_pickle(o):
    """
    Hamcrest expression that checks that the item cannot be pickled.
    """
    assert_that(calling(pickle.dumps).with_args(o),
                raises(TypeError))

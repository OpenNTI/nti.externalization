#!/usr/bin/env python
# -*- coding: utf-8 -*-


__all__ = [
    'to_external_object',
    'to_external_representation',
    'to_standard_external_dictionary',
    'new_from_external_object',
    'update_from_external_object',
]

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_standard_external_dictionary

from nti.externalization.representation import to_external_representation
from nti.externalization.internalization import new_from_external_object
from nti.externalization.internalization import update_from_external_object

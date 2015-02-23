import codecs
from setuptools import setup, find_packages

VERSION = '0.0.0'

import platform
py_impl = getattr(platform, 'python_implementation', lambda: None)
IS_PYPY = py_impl() == 'PyPy'

entry_points = {
	'console_scripts': [
	],
}

TESTS_REQUIRE = [
	'fudge',
	'nose',
	'nose-timer',
	'nose-pudb',
	'nose-progressive',
	'nose2[coverage_plugin]',
	'pyhamcrest',
	'zope.testing',
	'nti.testing'
]

setup(
	name='nti.externalization',
	version=VERSION,
	author='Jason Madden',
	author_email='jason@nextthought.com',
	description="NTI ZODB",
	long_description=codecs.open('README.rst', encoding='utf-8').read(),
	license='Proprietary',
	keywords='JSON Externalization Internalization',
	classifiers=[
		'Intended Audience :: Developers',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.3',
		'Programming Language :: Python :: 3.4',
		'Programming Language :: Python :: Implementation :: CPython'
	],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	namespace_packages=['nti'],
	tests_require=TESTS_REQUIRE,
	install_requires=[
		'setuptools',
		'isodate',
		'persistent',
		'PyYAML',
		'pytz',
		'simplejson',
		'six',
		'zc.intid',
		'ZODB',
		'zope.cachedescriptors',
		'zope.component',
		'zope.configuration',
		'zope.deferredimport',
		'zope.deprecation',
		'zope.dottedname',
		'zope.dublincore',
		'zope.event',
		'zope.interface',
		'zope.lifecycleevent',
		'zope.location',
		'zope.mimetype',
		'zope.preference',
		'zope.schema',
		'zope.security',
		'nti.common',
		'nti.ntiids',
		'nti.nose_traceback_info',
		'nti.zodb'
	],
	extras_require={
		'test': TESTS_REQUIRE,
	},
	dependency_links=[
		'git+https://github.com/NextThought/nti.nose_traceback_info.git#egg=nti.nose_traceback_info'
	],
	entry_points=entry_points
)

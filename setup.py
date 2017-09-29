import codecs
from setuptools import setup, find_packages

entry_points = {
    'console_scripts': [
    ],
}

TESTS_REQUIRE = [
    'nti.testing',
    'zope.testrunner',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.externalization',
    version='1.0.0.dev0',
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description="NTI Externalization",
    long_description=(_read('README.rst') + '\n\n' + _read('CHANGES.rst')),
    license='Apache',
    keywords='externalization',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.externalization",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'setuptools',
        'BTrees',
        'isodate',
        'nti.schema',
        'persistent',
        'PyYAML',
        'pytz',
        'simplejson',
        'six >= 1.11.0', # for the reference cycle fix in reraise()
        'ZODB',
        'zope.component',
        'zope.configuration',
        'zope.container',
        'zope.deferredimport',
        'zope.deprecation >= 4.3.0',
        'zope.dottedname',
        'zope.dublincore',
        'zope.event',
        'zope.hookable',
        'zope.interface',
        'zope.intid',
        'zope.lifecycleevent',
        'zope.location',
        'zope.mimetype >= 2.3.0',
        'zope.proxy',
        'zope.schema',
        'zope.security',
    ],
    extras_require={
        ':platform_python_implementation=="CPython"': [
            'cytoolz >= 0.8.2',
        ],
        ':platform_python_implementation=="PyPy"': [
            'toolz',
        ],
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
        ],
        'benchmarks': [
            'perf',
        ],

    },
    entry_points=entry_points,
)

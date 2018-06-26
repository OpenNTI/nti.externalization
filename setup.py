import os
import sys
import codecs

from setuptools import setup
from setuptools import find_packages
from setuptools import Extension

PYPY = hasattr(sys, 'pypy_version_info')

entry_points = {
    'console_scripts': [
    ],
}

TESTS_REQUIRE = [
    'fudge',
    'nti.testing',
    'zope.testrunner',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()

# Cython

try:
    from Cython.Build import cythonize
except ImportError:
    # The .c files had better already exist, as they should in
    # an sdist. Based on code from
    # http://cython.readthedocs.io/en/latest/src/reference/compilation.html#distributing-cython-modules
    def cythonize(extensions, **_kwargs):
        for extension in extensions:
            sources = []
            for sfile in extension.sources:
                path, ext = os.path.splitext(sfile)
                if ext in ('.pyx', '.py'):
                    ext = '.c'
                    sfile = path + ext
                sources.append(sfile)
            extension.sources[:] = sources
        return extensions

def cythonize1(ext):
    new_ext = cythonize(
        [ext],
        annotate=True,
        #compiler_directives={'linetrace': True}
    )[0]
    return new_ext

ext_modules = []

# Modules we want to compile with Cython. These *should* have a parallel
# .pxd file (with a leading _) defining cython attributes.
# They should also have a cython comment at the top giving options,
# and mention that they are compiled with cython on CPython.
# The bottom of the file must call import_c_accel.
# We use the support from Cython 28 to be able to parallel compile
# and cythonize modules to a different name with a leading _.
# This list is derived from the profile of bm_simple_iface
# https://github.com/NextThought/nti.externalization/commit/0bc4733aa8158acd0d23c14de2f9347fb698c040
if not PYPY:
    # Cython cannot properly handle double leading underscores, so
    # our implementation modules can't start with an underscore.
    for mod_name in (
            'base_interfaces', # private
            'datastructures',
            'externalization',
            'internalization',
            'singleton',
    ):
        ext_modules.append(
            cythonize1(
                Extension(
                    'nti.externalization._' + mod_name,
                    sources=["src/nti/externalization/" + mod_name + '.py'],
                    depends=["src/nti/externalization/_" + mod_name + '.pxd'],
                    #define_macros=[('CYTHON_TRACE', '1')],
                )))

setup(
    name='nti.externalization',
    version='1.0.0a2.dev0',
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
    ext_modules=ext_modules,
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

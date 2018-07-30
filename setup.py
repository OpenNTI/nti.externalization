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
    'manuel',
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
    def _source(m, ext):
        m = m.replace('.', '/')
        return 'src/nti/externalization/' + m + '.' + ext
    def _py_source(m):
        return _source(m, 'py')
    def _pxd(m):
        return _source(m, 'pxd')
    def _c(m):
        return _source(m, 'c')
    # Each module should list the python name of the
    # modules it cimports from as deps. We'll generate the rest.
    # (Not that this actually appears to do anything right now.)

    for mod_name, deps in (
            ('singleton', ()),
            ('_base_interfaces', ()),
            ('internalization.legacy_factories', ()),
            ('internalization.factories', ()),
            ('internalization.fields', ()),
            ('internalization.events', ('_interface_cache',)),
            ('internalization.externals', ()),
            ('internalization.updater', ()),
            ('externalization.fields', ('_base_interfaces',)),
            ('externalization.standard_fields', (
                '_base_interfaces',
                '_fields',
            )),
            ('externalization.dictionary', ('_base_interfaces',)),
            ('externalization.externalizer', ('_base_interfaces',)),
            ('externalization.decorate', ()),
            #('externalization', ('_base_interfaces',)),
            ('_interface_cache', ()),
            ('datastructures', (
                '_base_interfaces',
                '_interface_cache',
                'externalization',
                'internalization')),
    ):
        deps = ([_py_source(mod) for mod in deps]
                + [_pxd(mod) for mod in deps]
                + [_c(mod) for mod in deps])

        source = _py_source(mod_name)
        # 'foo.bar' -> 'foo._bar'
        mod_name_parts = mod_name.rsplit('.', 1)
        mod_name_parts[-1] = '_' + mod_name_parts[-1]
        mod_name = '.'.join(mod_name_parts)


        ext_modules.append(
            Extension(
                'nti.externalization.' + mod_name,
                sources=[source],
                depends=deps,
                define_macros=[('CYTHON_TRACE', '1')],
            ))

    ext_modules = cythonize(
        ext_modules,
        annotate=True,
        compiler_directives={
            #'linetrace': True,
            'infer_types': True,
        },
    )

setup(
    name='nti.externalization',
    version='1.0.0a5',
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description="NTI Externalization",
    long_description=(_read('README.rst') + '\n\n' + _read('CHANGES.rst')),
    license='Apache',
    keywords='externalization',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
        'transaction >= 2.2',
        'six >= 1.11.0', # for the reference cycle fix in reraise()
        'ZODB',
        'zope.component',
        'zope.configuration',
        'zope.container',
        'zope.dottedname',
        'zope.dublincore',
        'zope.event',
        'zope.hookable >= 4.2.0',
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

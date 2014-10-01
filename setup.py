"""
Links
`````
* `documentation
  <http://pythonhosted.org/pyramid_storage/>`_
* `development version
  <https://github.com/danjac/pyramid_storage>`_

"""

from setuptools import setup, Command


class PyTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        import subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


docs_extras = [
    'Sphinx',
    'docutils',
    'repoze.sphinx.autointerface',
]

tests_require = [
    'pytest',
    'mock',
]


setup(
    name='pyramid_storage',
    cmdclass={'test': PyTest},
    version='0.0.8',
    license='BSD',
    author='Dan Jacob',
    author_email='danjac354@gmail.com',
    description='File storage package for Pyramid',
    long_description=__doc__,
    url="",
    packages=[
        'pyramid_storage',
    ],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'pyramid',
    ],
    tests_require=tests_require,
    extras_require={
        'docs': docs_extras,
    },
    test_suite='pyramid_storage',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        "Topic :: Communications :: Email",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Framework :: Pyramid",
    ]
)

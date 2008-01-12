from setuptools import setup, find_packages
import sys, os

version = '0.3'

setup(name='jsonstore',
      version=version,
      description="A RESTful exposed database for arbitraty JSON objects.",
      long_description="""\
This package contains a WSGI app implementing a REST store accessible through a JSON syntax.""",
      classifiers=[], # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Roberto De Almeida',
      author_email='roberto@dealmeida.net',
      url='http://dealmeida.net/projects/jsonstore',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          'WebOb',
          'simplejson',
          'uuid',
      ],
      extras_require={
          'mysql': ['MySQL-python'],
          'sqlite': ['pysqlite>=2'],
      },
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = jsonstore.store:make_app

      [jsonstore.backend]
      mysql = jsonstore.backends.mysql:EntryManager
      sqlite = jsonstore.backends.sqlite:EntryManager
      """,
      )
      

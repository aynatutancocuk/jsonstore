from setuptools import setup, find_packages
import sys, os

version = '0.3a7'

setup(name='jsonstore',
      version=version,
      description="A RESTful exposed database for arbitrary JSON objects.",
      long_description="""\
This package contains a WSGI app implementing a REST store accessible through a JSON syntax.""",
      classifiers=[], # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Roberto De Almeida',
      author_email='roberto@dealmeida.net',
      url='http://jsonstore.org/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'shove',
          'Paste',
          'PasteScript',
          'PasteDeploy',
          'WebOb',
          'simplejson',
          'uuid',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = jsonstore.rest:make_app

      [paste.paster_create_template]
      jsonstore = jsonstore.template:JsonstoreTemplate
      """,
      )
      

from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(name='jsonstore',
      version=version,
      description="A RESTful Atom store using a JSON representation.",
      long_description="""\
This package contains a WSGI app implementing an Atom store accessible through a JSON syntax.""",
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
          'Paste',
          'shove',
          'httpencode',
          'simplejson',
      ],
      extras_require={
          'xml': ['ElementTree'],
      },
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = jsonstore.jsonstore:make_app

      [httpencode.format]
      name rabbitfish = jsonstore.rabbitfish:rabbitfish [xml]
      text/xml to python = jsonstore.rabbitfish:rabbitfish [xml]
      application/xml to python = jsonstore.rabbitfish:rabbitfish [xml]
      """,
      )
      

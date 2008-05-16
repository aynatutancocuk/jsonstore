import os

from paste.script import templates

class JsonstoreTemplate(templates.Template):

    summary = "JSONStore is a REST Microapp that stores JSON documents."
    
    egg_plugins = ['jsonstore']
    _template_dir = 'paster_templates'
    use_cheetah = False

    def post(self, command, output_dir, vars):
        if command.verbose:
            print '*'*72
            print '* Run "paster serve %s/server.ini" and open' % output_dir
            print '* http://localhost:8080/admin.html'
            print '*'*72

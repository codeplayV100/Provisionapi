import os
import urlparse
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple
from handlers import *


# noinspection PyPep8Naming
class apiapp(object):
    def __init__(self, custommaps, handlers):
        self.map = custommaps
        self.handlers = handlers

    def dispatch(self, request):
        adapter = self.map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            for key,value in values.iteritems():
                if key not in request.environ:
                    request.environ[key] = value
            resp = self.handlers[endpoint](request)
            return resp
        except HTTPException, e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)



routemaps = Map([
                  Rule('/app/accounts/<shortid>',endpoint='accounts'),
                  Rule('/app/accounts/', endpoint='accounts'),
                  Rule('/app/accounts',endpoint='accounts'),
                  Rule('/app/jobs',endpoint='acounts')
                  ])

handlers = {'accounts': accounts}
appli = apiapp(routemaps, handlers)

print "All Done"
run_simple('127.0.0.1', 5000, appli)

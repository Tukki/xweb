'''
Created on 2012-8-30

@author: lifei
'''
class SubDomainDispatcherMiddleware(object):
    """Allows one to mount middlewares or applications in a WSGI application.
    This is useful if you want to combine multiple WSGI applications::

        app = DispatcherMiddleware(app, {
            '/app2':        app2,
            '/app3':        app3
        })
    """

    def __init__(self, app, mounts={}):
        self.app = app 
        self.mounts = mounts

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', '').lower()
        app = self.mounts.get(host, self.app)
        return app(environ, start_response)

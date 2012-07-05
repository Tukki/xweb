from controller import XController
from process import XProcess

from werkzeug.routing import Rule, Map
from werkzeug.debug import DebuggedApplication
from config import XConfig



class XApp:
    
    def __init__(self):
        self.rewrite_rules = []
        self.loadConfig()
    
    def runApp(self, environ, start_response):
        return XProcess(self, environ, start_response).run()

    def loadConfig(self):
        try:
            if not self.rewrite_rules:
                _rules = XConfig.get('rewrite_rules')
                if isinstance(_rules, list):
                    for rule, endpoint in _rules:
                        self.rewrite_rules.append(Rule(rule, endpoint=endpoint))
        except:
            pass
    
        self.rewrite_rules.extend( [
                Rule('/<c>/<a>/',     endpoint='',        ),
                Rule('/<c>/',         endpoint='a=index',     ),
                Rule('/',             endpoint='c=default&a=index',),
            ])
        
        self.url_map = Map(self.rewrite_rules)
        
    def run(self):
        from werkzeug.serving import run_simple
        run_simple('0.0.0.0', 5000, self.runApp, use_reloader=True, use_debugger=True)    
        
    def runDebug(self):
        from werkzeug.serving import run_simple
        app = DebuggedApplication(self.runApp, evalex=True)
        run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)
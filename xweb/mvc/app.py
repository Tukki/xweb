

from werkzeug.debug import DebuggedApplication #@UnresolvedImport
from werkzeug.serving import run_simple #@UnresolvedImport
from xweb.config import XConfig
from process import XProcess
import re
import logging


re.compile("\(\?P<([^>]+)>\)")

keys_regex = re.compile('<([^|>]+)(?:\|([^>]+))?>', re.DOTALL)

class RewriteRule:
    
    def __init__(self, regex, params):
        self.params = params
        self.keys = {}
        keys = keys_regex.findall(regex)
        
        for key, value in keys:
            self.keys[key] = re.compile('^%s$' % value if value else '[^/]+')
        
        def func(m):
            if not m.group(2):
                return "(?P<%s>[^/]+)"%m.group(1)
            else:
                return "(?P<%s>%s)"%(m.group(1), m.group(2))
            
        pattern = "^%s$"%keys_regex.sub(func, regex)
        self.pattern = re.compile(pattern)
        self.urlfor = keys_regex.sub('%(\g<1>)s', regex)
        self.regex = regex
        
    def parseUrl(self, path_info):
        if not self.pattern.match(path_info):
            return None
        
        match = self.pattern.search(path_info)
        
        params = []
        
        for k in match.groupdict():
            v = match.groupdict().get(k)
            params.append("%s=%s" % (k, v) )
            
        for k in self.params:
            params.append("%s=%s" % (k, self.params.get(k)) )

        return "&".join(params)
        
        
    def createUrl(self, route, params):
        assert isinstance(params, dict)
        
        controller, action = route.strip().split("/")

        params['c'] = controller
        params['a'] = action
        
        for key in self.keys:
            pattern = self.keys.get(key)
            
            param = params.get(key)
            
            if not param:
                return False
            
            if not pattern.match(str(param)):
                return False
            
            
        for key in self.params:
            
            param = params.get(key)
            
            if param is not None and param != self.params.get(key):
                return False
            
            
        default = {}
        more = []
        
        
        for key in params:
            if key in self.params:
                continue
            
            pattern = self.keys.get(key)
            
            if not pattern:
                more.append( "%s=%s" % (key, params.get(key)))
            else:
                default[key] = params.get(key)
                
                
        url = self.urlfor % default
        
        if not more:
            return url
        
        if url.find("?")>-1:
            return url + "&" + "&".join(more)
        else:
            return url + "?" + "&".join(more)
        


class XApp:
    
    def __init__(self):
        self.rewrite_rules = []
        self.loadConfig()
    
    def runApp(self, environ, start_response):
        return XProcess(self, environ, start_response).run()

    def loadConfig(self):
        try:
            if not self.rewrite_rules:
                rules = XConfig.get('rewrite_rules')
                if isinstance(rules, list):
                    self.buildRewrite(rules)
        except:
            pass
        
        XConfig.App = self
        return self
        
    def buildRewrite(self, rules):
        self.rewrite_rules = []
        for rule in rules:
            self.rewrite_rules.append(RewriteRule(*rule))
            
        self.rewrite_rules.extend([
            RewriteRule('/',                  {'c':'default', 'a':'index'}),
            RewriteRule('/<c>/',              {'a':'index'}),
            RewriteRule('/<c>/<a>/',          {}),
        ])
        
    def createUrl(self, route, params):
        for rule in self.rewrite_rules:
            url = rule.createUrl(route, params)
            
            if url:
                return url
        
    def run(self):
        run_simple('0.0.0.0', 5000, self.runApp, use_reloader=True, use_debugger=True)    
        
    def runDebug(self):
        app = DebuggedApplication(self.runApp, evalex=True)
        run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)
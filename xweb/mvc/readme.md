# XWEB框架 MVC模块

李 飞 <lifei@7v1.net>

v1.0 2012-06-08 创建
v1.1 2012-08-30 增加了设计原则

## 设计原则

### 请求属性

#### 什么是请求的属性？

请求的属性就是只属于这个（类）请求的一些性质，例如：mimetype, content_type, ajax等。
XWEB框架中提到的请求的属性不随请求而变的，Response的属性。
举例来说:

1. 一个ajax请求要求返回json格式的数据，那么不论运行中有无异常，其返回的结果都要是json格式。
2. 一个请求要求返回utf-8编码的数据，其返回的数据都要是utf-8编码的。
3. 一个请求始终都不需要更改数据库（只做展示），那这个请求读写的属性就是只读。
4. 一个订单POST的请求所读取的任何数据原则上是不应该被缓存的，即这个请求的缓存属性是不缓存。

#### XWEB框架对请求属性的处理

在XWEB框架中设置这些属性都非常简单，我们采取了一种非常巧妙的办法让设置这些属性更优雅，当然这种做法有潜在的风险

* 代码: admin.py

        class AdminController(XController):

            def doOrderApi(self, mimetype='json'):
                pass

            def doShowProduct(self, read_only=True):
                pass


            def doApi4GBK(self, charset='gbk'):
                pass

            def doView(self):
                
                if self.is_xhr:
                    self.setContentType('json')
                else:
                    self.setContentType('html')

### 继承是代码复用的最好方式之一

XWEB框架认为类的继承可以实现拦截器、MiddleWare等设计的功能，因为，在XWEB框架中，废弃了拦截器和中间件的相关设计

如果，我们需要一个登陆验证，我们只需要将验证逻辑覆写到beforeAction方法即可。

* 代码: admin.py

        LoginController(XController):

            def beforeAction(self):
                if not self.secure_cookies.get('sid'):
                    if self.is_xhr:
                        self.json = {'message':'error', 'reason':'no login'}
                    else:
                        self.redirect( self.createUrl('login', next=self.request.referer) )
                    return False

                return True


        AdminController(LoginController):
            
            def doList(self):
                pass


或者需要编写一个错误页面：

* 代码: admin.py

        AdminController(XController):

            def handleException(self,**kwargs):
            '''异常处理
            如果其类型是JSON，如API，或者是AJAX调用，则返回JSON格式的错误
            当然有些时候，API或者AJAX也可以直接返回500错误
            如果不是JSON格式的，则返回一个美化过的500页面
            '''
            
            	if self.content_type == 'json' or self.is_xhr:
            		self.json['code'] = 0
        		else:
	                self.data = self.app.render('error/index.html', {})


###App的结构

在一个项目中，有一些代码是需要所有的子项目都需要的，例如：领域实体、Service等，有些东西又是子项目特有的，例如：模板、Controller。

在XWEB框架中，子项目被称之为App，每个子项目都会有一个XApplication的类（或子类）的实例。

####每个App启动一个wsgi

如果是每个子项目启动一个uwsgi，则入口代码可以写成：

* 代码: __init__.py

        www_app = XApplication('www',  'www')
        
        if __name__ == '__main__':
            www_app.run()
            
####多个App共用一个wsgi

如果是多个子项目共用一个uwsgi，则入口代码可以写成（调试）：

生产环境部署可有使用NGINX反响代理来代替SubDomainDispatcherMiddleware

* 代码: __init__.py

        from xweb.util import SubDomainDispatcherMiddleware
        
        www_app = XApplication('www',  'www').createApp()
        admin_app = XApplication('admin',  'admin').createApp()
        user_app = XApplication('user',  'user').createApp()
        
        main_app = SubDomainDispatcherMiddleware(www_app, {
                'admin.example.com':    admin_app,
                'user.example.com':     user_app,
            })
        
        if __name__ == '__main__':
            run_simple(’127.0.0.1’, 5000, app, use_debugger=True, use_reloader=True)

            

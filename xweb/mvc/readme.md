# XWEB框架 MVC模块

lifei <lifei@7v1.net>

v1.0 2012-06-08

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

在XWEB框架中设置这些属性都非常简单

* 代码: admin.py

        class AdminController(XController):

            @settings(mimetype='json', use_cache=False)
            def doOrder(self):
                pass

            @settings(read_only=True)
            def doShowProduct(self):
                pass


            @settings(charset='gbk', mimetype='xml')
            def doApi4GBK(self):
                pass

            def doView(self):
                
                if self.is_xhr:
                    self.setContentType('json')
                else:
                    self.setContentType('html')

### 继承是代码复用的最好方式之一

XWEB框架认为类的继承可以实现拦截器、MiddleWare等设计的功能，例如，我们需要一个登陆验证，
我们只需要将验证逻辑覆写到beforeAction方法即可。

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
                
                self.setStatusCode('200')
                self.text = self.app.render('error/index.html', {})


## 使用说明

### 配置文件

* 代码: settings.py

        db = {
            'default': {
                'host': '127.0.0.1',
                'user': 'root',
                  'db': 'xweb',
             'charset': 'utf-8'
            },
            'userdb':  {
                'host': '127.0.0.1',
                'user': 'root',
                  'db': 'userdb',
             'charset': 'utf-8'
            },
        }
        cache = {
            'default: {
                'host': '127.0.0.1',
                'port': 12580
            }
        }
        
        
* 代码：domain.py

        class User(Entity):
        
            _keys = ['name', 'city_id']
            _belongs_to = {'city': ('city_id', City)}
            
            
        class City(Entity):
            
            _keys = ['name']
    
* 代码：console.py
    
        from settings import db, cache
        
        config = {
            'db':db,
            'cache':cache
        }
        
        XConfig.load(config)
        
        user = User.get(1)
        user.name = 'lifei'
        
        users = User.getMulti('city_id=%s', (10010,))
        
        for user in users:
            print user.city.name
        
        UnitOfWork.inst().commit()


## LazyLoad的1+N转化为1+1的巧妙设计
之前，我们经常会对orm的belongto的设计为LazyLoad，以减少join的次数，但是LazyLoad对于
某些业务场景会有性能的问题，如：

    users = User.getMulti([1,2,3,4,5,6])
    
    for user in users:
        print user.city.name
        
每一次循环都会进行一次数据库查询。一般的解决方案是Eager Load，上面的代码会被更改为：

    users = User.with('city').getMulti([1,2,3,4,5])

即：查询列表的时候，就告诉orm说我想把city的数据一起取回来，于是系统会根据参数的设置
将相对应的city数据使用Join语句一同取回来，实现了1+N到1的过程。

xweb框架由于使用了UnitOfWork技术，因此对实体的管理就会更加方便、灵活。基于此，我们
设计出一种自动的Eager Load的技术，简单可以理解为如下：

    users = User.getMulti([1,2,3,4,5,6])
    city_ids = [user.id for user in users]
    citys = City.getMulti(city_ids)
    
    for user, city in zip(users, citys):
        print user.city.name
        
这样的话，通过两次列表查询将所有的数据取出，由1+N转化为1+1。
但是我们的业务代码却远比上面优雅，事实上，它与之前的代码没有任何差别：

    users = User.getMulti([1,2,3,4,5,6])
    
    for user in users:
        print user.city.name

一切的功能都是由框架自动完成的，不需要程序员去指定Eager Load的字段

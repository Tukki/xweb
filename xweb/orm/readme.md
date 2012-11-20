# XWEB框架 ORM模块

lifei <lifei@7v1.net>

v1.0 2012-06-08

##数据的层次

##使用说明

###配置文件

已全面升级

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

		@entity
        class City(Entity):
            
            name = XStringField()
        
        @entity    
        class User(Entity):
        
            name = XStringField()
            city_id = XIntField()
            city = XBelongsToField('city_id', City)
    
* 代码：console.py
    
        from settings import db, cache
        
        config = {
            'db':db,
            'cache':cache
        }
        
        XConfig.load(config)
        
        user = User.get(1)
        user.name = 'lifei'
        
        users = User.filter(User.city_id==10010).all()
        
        for user in users:
            print user.city.name
        
        UnitOfWork.inst().commit()


## LazyLoad的1+N转化为1+1的巧妙设计
之前，我们经常会对orm的belongto的设计为LazyLoad，以减少join的次数，但是LazyLoad对于
某些业务场景会有性能的问题，如：

    users = User.getList([1,2,3,4,5,6])
    
    for user in users:
        print user.city.name
        
每一次循环都会进行一次数据库查询。一般的解决方案是Eager Load，上面的代码会被更改为：

    users = User.with('city').getList([1,2,3,4,5])

即：查询列表的时候，就告诉orm说我想把city的数据一起取回来，于是系统会根据参数的设置
将相对应的city数据使用Join语句一同取回来，实现了1+N到1的过程。

xweb框架由于使用了UnitOfWork技术，因此对实体的管理就会更加方便、灵活。基于此，我们
设计出一种自动的Eager Load的技术，简单可以理解为如下：

    users = User.getList([1,2,3,4,5,6])
    city_ids = [user.id for user in users]
    citys = City.getList(city_ids)
    
    for user, city in zip(users, citys):
        print user.city.name
        
这样的话，通过两次列表查询将所有的数据取出，由1+N转化为1+1。
但是我们的业务代码却远比上面优雅，事实上，它与之前的代码没有任何差别：

    users = User.getList([1,2,3,4,5,6])
    
    for user in users:
        print user.city.name

一切的功能都是由框架自动完成的，不需要程序员去指定Eager Load的字段
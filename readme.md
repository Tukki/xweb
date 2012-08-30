#XWEB框架
作者：lifei   <lifei@7v1.net>

XWEB框架是一款基于python语言的Web开发框架

开发这个框架的目的:

1. 现有框架如Django, SQLAlchemy无法解决实际开发过程的一些问题，如短事务，N+1等。
2. 现有框架如Django, SQLAlchemy设计地过于复杂，各种坑爹配置，没有统一的标准，让使用者无从下手或者无法精通。

##特性

1. 一个轻量级的MVC框架和ORM框架
2. 采用工作单元来组织数据模型，提供级联查询，延时加载，N+1=>1+1，短事务和Identity Map等特性，能有效防止数据库死锁的发生。
3. ConnectionManager管理工作单元内的数据库链接，支持跨库提交，跨库事务等。

##主要思想

马丁福勒的《企业应用架构模式》一书

##原则

###设计思想

本框架有一个ORM框架和一个MVC框架构成，其主要设计思想如下：

1. 每个域名一个App，启动单独的uwsgi，如需要泛域名、静态化等需求，请在nginx层处理。
2. 一组App组成一个站点，其共用领域实体类，Service等，但是有各自的controllers和templates，如：www、admin等。目录结构如下：

    /domain         - 领域文件夹
        /entity         - 领域实体类
        /object         - 非领域实体类
        /service        - 领域服务类
    /www            - www子App
        /controller     - 控制器类
        /templates      - 模板文件夹
    /admin          - admin子App
        /controller
        /templates
    /config         - 配置文件目录

3. App只负责业务逻辑和展示页面，数据库操作、基本的缓存等由框架负责处理，一般情况下，程序员不需要关心。

###设计原则
1. 脚本即配置，且配置文件全局唯一
2. 约定优于配置，一切不涉及旧系统迁移的规则一律不再设置配置选项，例如：模板存放, action标识码等
3. 基于MVC架构，抛弃MVT模式，业务逻辑依托类来组织
4. 数据库链接、Cache链接等全部采用LazyLoad模式加载，由ConnectionManager和CacheManager统一管理，不提供预加载，减少分库时链接
5. 从代码组织上讲，分库优于分表，因此不提供分表功能，请大家尽量采用分库来代替分表
6. 轻量级，可运行于console程序
7. 数据库表名含义明确，全局唯一，例如：admindb中的user表表示管理员用户，而wwwdb中的user表表示注册用户，是不允许的，至少加上前缀，如admin_user
8. 类名全局唯一，虽然Python提倡module的概念，也有支持package命名空间，但是类名重复对业务代码组织及维护有百害而无一，坚决杜绝这种设计

##名词解释

> App: 以域名划分，例如，一个项目有前台，后台，图片等服务，分别为www.xxx.com, admin.xxx.com和img.xxx.com，则分别对应www,admin和img的app

> Controller: 以业务需求划分，例如：用户相关操作，订单操作分别属于UserController和OrderController，需要登录的在Controller的基类中实现或者在before方法中实现

> Action: 一次具体的请求，如：下单，可标示为: controller/action，此为默认地址，rewrite规则书写方式为: c=controller&a=action。



##编码规范

变量名：unix命名法

函数名：骆驼命名法

类名：  匈牙利命名法
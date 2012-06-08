# xweb框架
作者：lifei   <lifei@7v1.net>

xweb框架是一款基于python语言的Web开发框架

开发这个框架的目的是因为现有的一些框架无法解决实际开发过程的一些问题，如短事务，N+1等


# 原则

1. 脚本即配置，且配置文件全局唯一
2. 约定优于配置，一切不涉及旧数据迁移的规则一律不再设置配置选项，例如：模板存放, action标识码等
3. 基于MVC架构，抛弃MVT模式，业务逻辑依托类来组织代码
4. 数据库链接、Cache链接等全部采用LazyLoad模式加载，不提供预加载，减少分库时链接
5. 从代码组织上讲，分库优于分表，因此不提供分表功能，请大家尽量采用分库来代替分表
6. 轻量级，可运行于console程序


# 特性
1. 采用工作单元来组织数据模型，提供级联查询，延时加载，N+1，短事务，二级缓存和Identity Map等特性
2. 提供一个内置的ID生成器，支持跨库

# 名词解释

App: 以域名划分，例如，一个项目有前台，后台，图片等服务，分别为www.xxx.com, admin.xxx.com和img.xxx.com，则分别对应www,admin和img的app

Controller: 以业务需求划分，例如：用户相关操作，订单操作分别属于UserController和OrderController，需要登录的在Controller的基类中实现或者在before方法中实现

Action: 一次具体的请求，如：下单，可标示为: controller/action，此为默认地址，rewrite规则书写方式为: c=controller&a=action。



## 编码规范
变量名：unix命名法

函数名：骆驼命名法

类名：  匈牙利命名法
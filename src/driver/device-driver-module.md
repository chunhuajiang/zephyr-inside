---
title: Zephys OS 驱动篇：设备驱动模型
date: 2016-08-11 12:16:22
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文介绍 Zephyr OS 中的设备驱动模型，理解该模型是继续研究 Zephyr 中驱动程序的基础。
<!--more-->
# 前言
Zephyr OS 为所有的设备定义了一套设备驱动模型，这样做的好处是让所有的设备驱动程序、使用设备驱动的应用程序拥有一套框架。呃。。词乏，反正一句话，感觉棒棒哒。

单从这一点看上去，与 Linux 何其相似！

> 在 Contiki 中，各个驱动各自为政.

# 设备的描述

```
struct device {
	struct device_config *config;
	void *driver_api;
	void *driver_data;
};
```
struct device 用于描述一个设备，一共包含三个指针变量：
- struct device_config *config:设备的配置，见后面的描述。
- void *driver_api:设备对应的驱动的 API。
- void *driver_data:需要传递给设备对应的驱动的 API 的数据。

> 一会儿设备，一会儿驱动，这两者到底神马逻辑，当年看 linux 内核的时候，晕过很久。可以这样理解：
> 设备对应(描述)一个具体的硬件设备，而要使用该设备时，需要调用对应的驱动程序。
> 说白了，这其实是一种编程抽象思维，即如何把现实中的事物抽象成代码。


```
struct device_config {
	char	*name;
	int (*init)(struct device *device);
	void *config_info;
};
```
struct device_config 用于描述设备的配置，一个包含三个指针变量：
- char *name:设备的名字。这个很重要，它唯一地标识了一个设备。在编写应用程序时，应用程序就是使用设备的名字来获取整个设备的描述结构的。
- int (*init)(struct device *device):指向设备的初始化函数。在系统的启动过程中，会对系统中的所有设备进行初始化操作，具体接口将在后面介绍。
- void *config_info:这是设备具体的配置信息。

# 设备的分级
Zephyr OS 将系统的设备划分为五个等级：PRIMARY、SECONDAY、NANOKERNEL、MICROKERNEL和APPLICATION。其相关定义如下：

```
#define _SYS_INIT_LEVEL_PRIMARY      0
#define _SYS_INIT_LEVEL_SECONDARY    1
#define _SYS_INIT_LEVEL_NANOKERNEL   2
#define _SYS_INIT_LEVEL_MICROKERNEL  3
#define _SYS_INIT_LEVEL_APPLICATION  4
```
将设备分级的作用，是让系统在启动的不同阶段对不同等级设备进行初始化操作。在系统启动的最初始化阶段，会先初始化 PRIMARY 级的所有设备（即调用设备描述结构体中的 init 函数指针），再初始化 SECONDARY 级的所有设备，并依次在后续的启动过程中的不同阶段初始化不同级的设备。

# 设备的初始化

在讲设备的初始化之前，先看看设备的段分布情况。

在定义设备时（参考后面的**设备的定义**），会指定设备的等级，并将相同等级的设备放到同一个段中。这些段的起始地址分别是：
- \__device_init_start： 设备的起始地址
- \__device_PRIMARY_start：PRIMARY级设备的地址存放的起始地址，等于\__device_init_start
- \__device_SECONDARY_start：SECONDARY级设备的地址存放的起始地址
- \__device_NANOKERNEL_start：NANOKERNEL级设备的地址存放的起始地址
- \__device_MICROKERNEL_start：MICROKERNEL级设备的地址存放的起始地址
- \__device_APPLICATION_start：APPLICATION级设备的地址存放的起始地址
- \__device_init_end：设备的结束地址

> 上面的内容涉及到链接脚本的内容，如果感兴趣可以阅读《Zephyr OS 番外篇：链接脚本语法详解》和《Zephyr OS 番外篇：链接脚本 linker.ld 详解》。如果不感兴趣，直接记住上面的结论即可。

---

设备的初始化函数如下：
```
static struct device *config_levels[] = {
	__device_PRIMARY_start,
	__device_SECONDARY_start,
	__device_NANOKERNEL_start,
	__device_MICROKERNEL_start,
	__device_APPLICATION_start,
	__device_init_end,
};

void _sys_device_do_config_level(int level)
{
	struct device *info;

	// 以 info < config_levels[level+1] 作为 for 循环的结束判断条件，是因为各级
    // 设备的存放地址是连续的，即存放完 PRIMARY 级设备后，紧接着就存放SECONDAY 级的设备
	for (info = config_levels[level]; info < config_levels[level+1]; info++) {
		struct device_config *device = info->config;

		device->init(info);
	}
}
```
函数很简单，根据传入的参数(需要初始化的设备的等级)，依次调用该级设备的初始化函数进行初始化。
# 设备的定义
在 Zephyr OS 中，设备的定义以宏实现。
```
#define DEVICE_AND_API_INIT(dev_name, drv_name, init_fn, data, cfg_info, \
			    level, prio, api) \
	\
	static struct device_config __config_##dev_name __used \
	__attribute__((__section__(".devconfig.init"))) = { \
		.name = drv_name, .init = (init_fn), \
		.config_info = (cfg_info) \
	}; \
	\
	static struct device (__device_##dev_name) __used \
	__attribute__((__section__(".init_" #level STRINGIFY(prio)))) = { \
		 .config = &(__config_##dev_name), \
		 .driver_api = api, \
		 .driver_data = data \
	}
```
一眼看上去好复杂，但是别怕，纸老虎：
- 首先，\__attribute__(xxx)这段代码不用管，它用于告诉编译器如何将这段代码放到段中。
- 然后，__used 也不同管管，原因同上。
- 最后，“##”是连接符，编译器会在预编译阶段将“##”和“##”后的内容连接起来。

所以，这段代码先定义了一个设备配置，再定义了一个设备，并对相应的成员变量进行赋值：
```
#define DEVICE_AND_API_INIT(dev_name, drv_name, init_fn, data, cfg_info, \
			    level, prio, api) 						\
	static struct device_config __config_dev_name   = { \
		.name = drv_name, 								\
        .init = (init_fn), 								\
		.config_info = (cfg_info) 						\
	}; 													\
														\
	static struct device (__device_dev_name) = { 		\
		 .config = &(__config_dev_name), 				\
		 .driver_api = api, 							\
		 .driver_data = data 							\
	}
```
系统中还有另外两个宏也可用于定义设备：
```
#define DEVICE_INIT(dev_name, drv_name, init_fn, data, cfg_info, level, prio) \
	DEVICE_AND_API_INIT(dev_name, drv_name, init_fn, data, cfg_info, \
			    level, prio, NULL)

define SYS_INIT(init_fn, level, prio) \
	DEVICE_INIT(sys_init_##init_fn, "", init_fn, NULL, NULL, level, prio)

```
其中，DEVICE_INIT()在定义时将驱动的API设为NULL，即该设备不提供驱动API；SYS_INIT()除了不提供驱动的API外，还不提供驱动的名字和配置、配置数据。
# 获取设备
在用于程序中，如果要使用设备驱动，则按照一下步骤：
- 根据驱动的名字获取设备。
- 调用设备的驱动程序或通过设备的配置调用相应的接口。

获取设备的函数如下：
```
struct device *device_get_binding(char *name)
{
	struct device *info;

	for (info = __device_init_start; info != __device_init_end; info++) {
		if (info->driver_api && !strcmp(name, info->config->name)) {
			return info;
		}
	}

	return NULL;
}
```
它从设备的首地址处开始依次查找设备，判断设备配置中配置的名字是不是需要查找的名字，如果是，则返回该设备。
> 程序中还做了一个判断，即设备的驱动 API 是否存在。因为有些设备是使用宏　DEVICE_INIT() 或 SYS_INIT() 定义的，它们没有设置驱动，是系统级的，不能由应用程序使用。

# 驱动开发流程
在 Zephyr OS 中，不仅在驱动的最外层定义了模板（即 device 的描述结构体），还对每一类设备定义了一套独立的子模板（即一套驱动接口以及一套设备配置）。具体而言，实现一个驱动的流程是这样的（以 uart 驱动为例）：
**内核层（实现驱动）：**
- 使用 DEVICE_AND_API_INIT 定义设备，并绑定设备的驱动程序、设备的配置。（也有例外，比如控制台驱动，具体原因请参考《Zephyr OS 驱动篇：Console 驱动与 Uart 驱动的关系》）
- 实现 OS 中定义的配置结构体 struct uart_device_config
- 根据配置的结果，实现设备的初始化函数。
- 实现 OS 中定义的 api 结构体 struct uart_driver_api（可以根据具体需求，只实现一部分函数）。

**应用层（测试驱动）：**
- 通过 device_get_binding 获取描述设备的结构体。
- 根据获取的结构体，取出该驱动的 API，将其转换为 struct uart_driver_api，然后调用这些 API 即可。
- 如果需要获取设备的配置信息，取出之，并将其转换为 struct uart_device_config，然后就可以使用这些配置了。
# 总结
当年看 Linux 的设备驱动模型时，只知道如何添加驱动程序，却始终没明白其思路，悲催悲催。还好，现在终于明白其中的来龙去脉了。开心开心～～
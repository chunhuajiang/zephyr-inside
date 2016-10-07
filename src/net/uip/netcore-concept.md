---
title: Zephys OS uIP 协议栈：net core - 核心概念
date: 2016-10-07 10:13:52
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Zephyr OS 对 uIP 协议栈进行了一个封装，对这个封装起了个名字 —— net core(网络的核心)。主要的源码位于`net/ip/netcore.[ch]`中。通过这个 net core，我们可以顺藤摸瓜，从全局掌握整个 uIP 协议栈的所有知识。

- [网络设备](#网络设备)
- [注册设备驱动程序](#注册设备驱动程序)
- [注销设备驱动程序](#注销设备驱动程序)
- [net core 提供的 API](#net-core-提供的-api)
    - [与应用程序交互](#与应用程序交互)
    - [与驱动程序交互](#与驱动程序交互)
- [总结](#总结)

<!--more-->

# 网络设备
在这个 net core 里面，定以了一个网络设备(这个网络设备只是一个概念，不争对具体的一个设备)：
```
static struct net_dev {
	struct nano_fifo rx_queue;
	struct nano_fifo tx_queue;
	// 注册到该网络设备的设备驱动程序
	struct net_driver *drv;
} netdev;

```
这个网络设备维护了两个全局的缓冲队列：
- tx_queue(发送缓冲队列)：一方面，当应用程序想发送数据时，会先传递到 net core，net core 会先对应用数据进行封装(应用层的头部、传输层的头部和网络层的头部)，然后将封装后的数据放到这个发送缓冲队列中。另一方面，网络设备的设备驱动程序会从这个发送缓冲队列中取出数据，对该数据进行分片、头部压缩等操作(这是可选的，依赖于所使用的底层协议)，然后再封装上 MAC 层和物理层的头部信息，然后由实际的设备(比如以太网芯片、蓝牙芯片、IEEE 802.15.4 芯片)将封装后形成的帧发送到网络信道中取。
- rx_queue(接收缓冲队列)：一方面，当实际的设备(比如以太网芯片、蓝牙芯片、IEEE 802.15.4 芯片)侦听到信道中的消息帧时，会将该消息帧传递给设备驱动程序，设备驱动程序会先对该帧进行解封装(MAC 层头部、物理层头部，以及可选的碎片重组、头部解压缩)，然后将解封装后的数据放到这个接收缓冲队列中。另一方面，net core 会从这个接收缓冲队列中取出数据，进行进一步接封装(网络层的头部、传输层的头部、应用层的头部)，然后传递给对应的应用程序。

设备所绑定的驱动的定义如下：
```
struct net_driver {
	/** How much headroom is needed for net transport headers */
	size_t head_reserve;

	/** Open the net transport */
	int (*open)(void);

	// 向网络中发送数据，其返回值：
    // 0 ：报文没有被发送。
    // 1 ：报文被成功发送。
    // <0：报文发送失败。
	int (*send)(struct net_buf *buf);
};
```
其具体作用已在上面解释过了。

# 注册设备驱动程序
争对每一类网络设备，Zephyr OS 都提供了一套对应的驱动，例如 802.15.4 驱动、蓝牙驱动、以太网驱动、回环驱动、slip 驱动(即 `net/ip/net_driver_xxxx.[ch]`)。这些驱动通过注册的方式绑定到 net core 所定义的网络设备：
```
int net_register_driver(struct net_driver *drv)
{
	int r;

	if (netdev.drv) {
    	// 设备已经绑定了其它驱动，返回错误码
		return -EALREADY;
	}

	// 代码走到这里，说明网络设备目前还未绑定驱动
    // 检查该驱动的 open 函数和 send 函数是否为空
	if (!drv->open || !drv->send) {
    	// open 函数或 send 函数为空，返回错误码。
		return -EINVAL;
	}

	// 代码走到这里，说明网络设备目前还未绑定驱动
    // open 该驱动
	r = drv->open();
	if (r < 0) {
    	// open 失败，返回由 open 返回的错误码
		return r;
	}
	
    // 驱动注册成功
	netdev.drv = drv;

	return 0;
}
```
我们可以看到，当网络设备已经绑定了驱动程序后，再注册其它驱动时，将注册失败。

# 注销设备驱动程序
```
void net_unregister_driver(struct net_driver *drv)
{	
	// 将驱动设置 NULL。
	netdev.drv = NULL;
}
```
当网络设备绑定的设备驱动被注销后，再注册其它驱动时，就可能会注册成功。

# net core 提供的 API
## 与应用程序交互
net core 暴露了三个接口给应用程序：
- net_init()：当应用程序需要使用协议栈时，需要先调用该函数对协议栈进行初始化
- net_send()：当应用程序需要发送数据时，需要调用该函数。
- net_receive()：当应用程序等待接收数据时，需要调用该函数。

## 与驱动程序交互
net core 暴露了一个接口给驱动程序：
- net_recv()：当驱动程序接收到信道中的消息时，需要调用该函数将消息传递给协议栈。

同时，驱动程序也暴露了接口给 net core，即网络设备所绑定的驱动程序：
- struct netdev.drv.open()：net core 初始化时会调用该函数。
- struct netdev.drv.send()：net core 发送消息时，会调用该函数。

# 总结

Zephyr OS 中提供的两个协议栈，无论是 uIP 还是 yaip，它们都封装了一层 net core，它们与应用程序和驱动程序交互的 API 是相同的，因此用户在写应用程序时，不用关心 uIP 协议栈和 yaip 协议栈的细节，只需要调用这些通用 API 就可以了。



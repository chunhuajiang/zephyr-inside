---
title: Zephys OS uIP 协议栈：net context - 续
date: 2016-10-11 22:13:43
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本节我们继续学习 net context 中的几个函数，并从整体上把握 net context 的概念。

- [contexts[] 的定义](#contexts[]-的定义)
- [net_context_get](#net_context_get)
- [net_context_put](#net_context_put)
- [总结](#总结)

# contexts[] 的定义
```
static struct net_context contexts[NET_MAX_CONTEXT];
```
net context 内部定义了一个全局的数组 contexts，这个数组的长度是 NET_MAX_CONTEXT。由于一个 struct net_context 就包含一个网络连接的上下文，所以，**在整个网络中，最多同时支持 NET_MAX_CONTEXT 个连接**。而 NET_MAX_CONTEXT 的默认值是 5，因此，在默认情况下，uIP 协议栈最多同时支持 5 个网络连接。

# net_context_get
编写网络应用程序的第一步，就是通过 net_context_get() 函数获取一个 context。

类似于 socket 编程中的创建 socket。

```
struct net_context *net_context_get(enum ip_protocol ip_proto,
				    const struct net_addr *remote_addr,
				    uint16_t remote_port,
				    struct net_addr *local_addr,
				    uint16_t local_port)
{
#ifdef CONFIG_NETWORKING_WITH_IPV6
	const struct in6_addr in6addr_any = IN6ADDR_ANY_INIT;
	const uip_ds6_addr_t *uip_addr;
	uip_ipaddr_t ipaddr;
#endif
	int i;
	struct net_context *context = NULL;

	/* User must provide storage for the local address. */
	if (!local_addr) {
		return NULL;
	}

#ifdef CONFIG_NETWORKING_WITH_IPV6
	......
#else
  // 如果使用 IPv4
	if (local_addr->in_addr.s_addr[0] == INADDR_ANY) {
    // 如果传入的 local_addr 为 0，自动填充本机地址
		uip_gethostaddr((uip_ipaddr_t *)&local_addr->in_addr);
	}
#endif

	nano_sem_take(&contexts_lock, TICKS_UNLIMITED);

	if (local_port) {
    // 如果传入的 local_port 不为 0 ，检查这个端口号是否已被其它 context 使用
		if (context_port_used(ip_proto, local_port, local_addr) < 0)
      // 端口号已被其它 context 使用，返回 NULL，表示获取 context 失败
			return NULL;
		}
	} else {
    // 如果传入的 local_port 为 0，表示让协议栈自动分配一个有效的端口号
		do {
      // 随机生成一个端口号
			local_port = random_rand() | 0x8000;
		} while (context_port_used(ip_proto, local_port, // 检查生成的端口号是否已被使用
					   local_addr) == -EEXIST);
	}

  // 遍历整个 contexts 数组
	for (i = 0; i < NET_MAX_CONTEXT; i++) {
		if (!contexts[i].tuple.ip_proto) {
      // 如果该 context 未被使用，则对该 context 的元组进行初始化
      // 它将成为本次获取到的有效 context。
			contexts[i].tuple.ip_proto = ip_proto;
			contexts[i].tuple.remote_addr = (struct net_addr *)remote_addr;
			contexts[i].tuple.remote_port = remote_port;
			contexts[i].tuple.local_addr = (struct net_addr *)local_addr;
			contexts[i].tuple.local_port = local_port;
			context = &contexts[i];
      // 退出 for 循环
			break;
		}
	}

	context_sem_give(&contexts_lock);

	/* Set our local address */
#ifdef CONFIG_NETWORKING_WITH_IPV6
	.....
#endif

  // 返回获取到的 context。
	return context;
}
```
看上去略微复杂，但是所做的事儿其实挺简单的：
- 如果 local_addr 为 0，自动填充本地 ip 地址为本机的地址。
- 如果 local_port 为 0，自动获取一个有效的端口号。
- 遍历 contexts 数组，查找一个未被使用的 context，然后设置该 context 的元组。

# net_context_put
如果应用程序的网络任务完成了，可以调用 net_context_put() 将它获取到的  context 还给系统。

类似于 socket 编程中的关闭 socket。

```
void net_context_put(struct net_context *context)
{
	if (!context) {
		return;
	}

	nano_sem_take(&contexts_lock, TICKS_UNLIMITED);

	if (context->tuple.ip_proto == IPPROTO_UDP) {
		if (net_context_get_receiver_registered(context)) {
			  // 如果该 context 注册了 dup，则将其注销
			  struct simple_udp_connection *udp =	net_context_get_udp_connection(context);
				simple_udp_unregister(udp);
		}
	}

#ifdef CONFIG_NETWORKING_WITH_TCP
	......
#endif

	// 再将该 context 的其它成员设置为初始状态
	memset(&context->tuple, 0, sizeof(context->tuple));
	memset(&context->udp, 0, sizeof(context->udp));
	context->receiver_registered = false;

	context_sem_give(&contexts_lock);
}
```
该函数的主要工作是设置 context 中各成员的值到初始状态，并处理一些相关的工作。

# 总结
在 net context 内部，定义了一个全局数组 contexts[]，应用程序如果需要与其它设备进行网络通信，需要从 net context 中申请获取一个 context。如果应用程序完成的所有的任务，就将申请到的 context 还给 net context。

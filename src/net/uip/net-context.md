---
title: Zephys OS uIP 协议栈：net context
date: 2016-10-10 23:42:41
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本节我们先学习 net context 的基本定义，以及基本的 API，主要是为后面的 net core 做一个铺垫。

- [net context 的结构体](#net-context-的结构体)
- [基本 API](#基本-api)
    - [net_context_init](#net_context_init)
    - [context_port_used](#context_port_used)
    - [net_context_get_tuple](#net_context_get_tuple)
    - [net_context_get_queue](#net_context_get_queue)
    - [net_context_get_udp_connection](#net_context_get_udp_connection)
    - [net_context_get_receiver_registered](#net_context_get_receiver_registered)
    - [net_context_set_receiver_registered](#net_context_set_receiver_registered)
    - [net_context_unset_receiver_registered](#net_context_unset_receiver_registered)

<!--more-->

# net context 的结构体
Zephyr OS 为 uIP 协议栈设计了一个 net context 结构，它主要用于描述网络连接的上下文。net context 的作用与传统 linux 中的套接字 socket 类似。
```
struct net_context {
	struct net_tuple tuple;
	struct nano_fifo rx_queue;

	union {
		struct simple_udp_connection udp;
#ifdef CONFIG_NETWORKING_WITH_TCP
      ......
#endif
	};

	bool receiver_registered;
};
```
主要成员：
- tuple：记录该 net context 的协议类型、本地的地址和端口号、远程的地址和端口号
- rx_queue：用于保存应用程序的接收数据。
- udp：一个简单 upd 连接。
- receiver_registered：主要用作 udp。udp 在发送数据前，需要进行一次注册。这里的 receiver_registered 就表示有没有进行注册。

# 基本 API
## net_context_init
初始化 context：
```
void net_context_init(void)
{
	int i;

  // 初始化锁 contexts_lock
	nano_sem_init(&contexts_lock);

  // 初始化 contexts 中的每个 context 是所有成员
	memset(contexts, 0, sizeof(contexts));

  // 初始化 contexts 中的每个 context 的接收队列
	for (i = 0; i < NET_MAX_CONTEXT; i++) {
		nano_fifo_init(&contexts[i].rx_queue);
	}

  // 释放锁 contexts_lock
	context_sem_give(&contexts_lock);
}
```
## context_port_used
判断一个本地端口是否在 contexts 中被使用。
```
static int context_port_used(enum ip_protocol ip_proto, uint16_t local_port,
			     const struct net_addr *local_addr)

{
	int i;

  // 依次遍历 contexs 数组中的每个元素
	for (i = 0; i < NET_MAX_CONTEXT; i++) {
		if (contexts[i].tuple.ip_proto == ip_proto &&
		    contexts[i].tuple.local_port == local_port &&
		    !memcmp(&contexts[i].tuple.local_addr, local_addr,
			   sizeof(struct net_addr))) {
			return -EEXIST;
		}
	}
	return 0;
}
```
> 有一点没想明白，为什么要判断 local_addr ？对于一个给定的设备，它的 local_addr 不应该是确定且唯一的嘛？

## net_context_get_tuple
返回一个 net context 的记录协议类型、本地地址和端口号、远程地址和端口号的元组。
```
struct net_tuple *net_context_get_tuple(struct net_context *context)
{
	if (!context) {
		return NULL;
	}

	return &context->tuple;
}
```
## net_context_get_queue
返回一个 net context 的接收队列。应用程序接收数据时就是从这个队列中取数据。
```
struct nano_fifo *net_context_get_queue(struct net_context *context)
{
	if (!context)
		return NULL;

	return &context->rx_queue;
}
```
## net_context_get_udp_connection
返回一个 net context 的简单 udp 连接数据。
```
struct simple_udp_connection * net_context_get_udp_connection(struct net_context *context)
{
	if (!context) {
		return NULL;
	}

	return &context->udp;
}
```
## net_context_get_receiver_registered
判断一个(UDP) 的 net context 是否注册了
```
int net_context_get_receiver_registered(struct net_context *context)
{
	if (!context) {
		return -ENOENT;
	}

	if (context->receiver_registered) {
		return true;
	}

	return false;
}

```
## net_context_set_receiver_registered
(UDP)注册以后，调用此函数，设置注册的标志为“已注册”
```
void net_context_set_receiver_registered(struct net_context *context)
{
	if (!context) {
		return;
	}

	context->receiver_registered = true;
}
```
## net_context_unset_receiver_registered
设置注册标志为“未注册”
```
void net_context_unset_receiver_registered(struct net_context *context)
{
	if (!context) {
		return;
	}

	context->receiver_registered = false;
}
```

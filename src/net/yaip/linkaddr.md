---
title: Zephys OS yaip 协议栈：link addr
date: 2016-10-19 20:21:14
categories: ["Zephyr OS"]
tags: [Zephyr]
---

- [TCP/IP 分层模型](#tcpip-分层模型)
- [链路地址的定义](#链路地址的定义)
- [链路地址使用举例](#链路地址使用举例)
- [存储链路地址](#存储链路地址)
- [比较两个链路地址](#比较两个链路地址)

# TCP/IP 分层模型

TCP/IP 的四层模型，从上到下依次是：
- 应用层，其协议包括：CoAP, Http, MQTT 等。
- 传输层，其协议包括：TCP，UDP。
- 网络层，其协议包括：IP，IPv6，ICMP，ICMPv6等；
- 数据链路层（具体细分为 MAC 层和物理层），其协议包括 IEEE 802.15.4，IEEE 802.3（因特网），IEEE 802.15.1（蓝牙）等。

在这四层模型中，涉及到两种地址：数据链路层的地址（通常所说的 MAC 地址）和网络层的地址（通常所说的 IP 地址）。我们先在本节学习数据链路层的地址相关的定义，并在下一节学习 IP 地址相关的定义。

在 Zephyr OS 里面，我们直接将数据链路层的地址叫做链路地址。链路地址相关的源码网位于`include/net/net_linkaddr.h`。

<!--more-->

# 链路地址的定义
```
struct net_linkaddr {
	uint8_t *addr;
	uint8_t len;
};
```
包含两个成员：
- addr：一个无符号字符类型的指针，指向链路地址所在的内存空间。
- len：该链路地址的长度，单位是字节。

可以看出来，struct net_linkaddr 这个结构体中本身并没有存储链路地址，而是指向了存储在其它地方的链路地址的内存空间。

# 链路地址使用举例
```
uint8_t src_mac[] = { 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0xaa, 0xbb };
struct net_linkaddr linkaddr;

linkaddr.addr = src_mac;
linkaddr.len = sizeof(src_mac[]);
```
我们单独在外面定义了一个数组，用来存放链路地址，而 linkaddr 只是指向了该数组而已。

# 存储链路地址
上面的 struct net_linkaddr 本身并没有存储链路地址，而只是指向了存放链路地址的内存空间。yaip 协议栈还定义了另一个结构体，可以存储链路地址：
```
struct net_linkaddr_storage {
	uint8_t len;

	union {
		uint8_t addr[0];
		struct {
			uint32_t storage[2];
		};
	};
};
```
其中，
- len：链路地址的长度，单位是字节。
- 联合体：
 - storage[2]: uint32_t 类型的数组，一共占 8 个字节。
 - addr[0]：一个柔性数组，它的作用是可以从这个联合体的存储空间一个字节一个字节地取地址。

整个联合体一共占 8 个字节，共 64 比特。这足够用来存储链路地址了，因为目前所有的链路层协议的链路地址，最多也就 64 比特。

# 比较两个链路地址
函数 net_linkaddr_cmp() 可以用来比较两个链路地址是否相等。
```
static inline bool net_linkaddr_cmp(struct net_linkaddr *lladdr1,
				    struct net_linkaddr *lladdr2)
{
  // 对入参的有效性检查
	if (!lladdr1 || !lladdr2) {
		return false;
	}

  // 如果两个地址的长度不相等，直接返回 false
	if (lladdr1->len != lladdr2->len) {
		return false;
	}

  // 两个地址的长度相等时，再进行比较
	return !memcmp(lladdr1->addr, lladdr2->addr, lladdr1->len);
}
```

---
title: Zephys OS uIP 协议栈：TCP/IP 的一些定义
date: 2016-10-10 21:25:1423
categories: ["Zephyr OS"]
tags: [Zephyr]
---

在正式进入 net context 的学习之前，先看看`include/net/uip/net_ip.h`文件中定义的宏和数据结构，这些宏和数据结构在 net context 中被广泛使用。

# 协议族 PF(protocol family)
```
#define PF_UNSPEC	0	 // 未指定协议族
#define PF_INET		2	 // IPv4 协议族
#define PF_INET6	10 // IPv6 协议族
```
# 地址族 AF(address family)
地址族与协议族一一对应：
```
#define AF_UNSPEC	PF_UNSPEC // 未指定
#define AF_INET		PF_INET   // IPv4 地址
#define AF_INET6	PF_INET6  // IPv6 地址
```
# 协议号
```
/** Protocol numbers from IANA */
enum ip_protocol {
	IPPROTO_TCP = 6,     // TCP 协议
	IPPROTO_UDP = 17,    // UDP 协议
	IPPROTO_ICMPV6 = 58, // ICMPv6 协议
};
```
说明一下，说明这个枚举结构叫做 ip_protocol，并不是指的网络层协议，而是指 tcp/ip协议。

# TCP 的类型
```
enum net_tcp_type {
	NET_TCP_TYPE_UNKNOWN = 0,
	NET_TCP_TYPE_SERVER,   // TCP 服务端
	NET_TCP_TYPE_CLIENT,   // TCP 客户端
};
```
# IPv6 地址
```
struct in6_addr {
	union {
		uint8_t		u6_addr8[16];
		uint16_t	u6_addr16[8]; /* In big endian */
		uint32_t	u6_addr32[4]; /* In big endian */
	} in6_u;
#define s6_addr			in6_u.u6_addr8
#define s6_addr16		in6_u.u6_addr16
#define s6_addr32		in6_u.u6_addr32
};
```
每个 IPv6 地址占 8*16 = 16*8 = 32*4 = 128 bit。

结构体里面定义的三个宏，是为了直接访问结构体里面定义的联合体。

# IPv4 地址
```
struct in_addr {
	union {
		uint8_t		u4_addr8[4];
		uint16_t	u4_addr16[2]; /* In big endian */
		uint32_t	u4_addr32[1]; /* In big endian */
	} in4_u;
#define s4_addr			in4_u.u4_addr8
#define s4_addr16		in4_u.u4_addr16
#define s4_addr32		in4_u.u4_addr32

#define s_addr			s4_addr32
};
```
每个 IPv4 地址占 8*4 = 16*2 = 32*1 = 32 bit。

结构体里面定义的四个宏，也是为了直接访问结构体里面定义的联合体。
# struct net_addr
```
struct net_addr {
	sa_family_t family;         // 表示使用的是哪个地址族
	union {
		struct in6_addr in6_addr; // IPv6 地址
		struct in_addr in_addr;   // IPv4 地址
	};
};
```
# 网络连接的元组
```
struct net_tuple {
	struct net_addr *remote_addr;
	struct net_addr *local_addr;
	uint16_t remote_port;
	uint16_t local_port;
	enum ip_protocol ip_proto;
};
```
上面的结构体用来表示一个网络连接的远程设备与本地设备相关的信息。

# 其它定义
```
// 定义了两个 TCP 的事件
enum tcp_event_type {
	TCP_READ_EVENT = 1,
	TCP_WRITE_EVENT,
};
```

```
#define IN6ADDR_ANY_INIT { { { 0, 0, 0, 0, 0, 0, 0, 0, 0, \
				0, 0, 0, 0, 0, 0, 0 } } }
#define IN6ADDR_LOOPBACK_INIT { { { 0, 0, 0, 0, 0, 0, 0, \
				0, 0, 0, 0, 0, 0, 0, 0, 1 } } }

#define INET6_ADDRSTRLEN 46
#define INADDR_ANY 0
```

---
title: Zephys OS uIP 协议栈：L2 Buffer - packet 属性
date: 2016-10-09 17:21:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---

包属性是 Contiki 里面的 Rime 协议栈定义的一个抽象概念，在 uIP 的协议栈里面会用到相关的几个函数，所以我们先简单地学习一下。

- [属性的类型](#属性的类型)
- [属性的定义](#属性的定义)
    - [ATTR 属性](#attr-属性)
    - [ADDR 属性](#addr-属性)
- [l2 buf 中定义的属性](#l2-buf-中定义的属性)
- [访问 l2 buf 中的属性](#访问-l2-buf-中的属性)
- [相关函数](#相关函数)
    - [packetbuf_attr_clear](#packetbuf_attr_clear)
    - [packetbuf_attr_copyto](#packetbuf_attr_copyto)
    - [packetbuf_attr_copyfrom](#packetbuf_attr_copyfrom)
    - [packetbuf_set_attr](#packetbuf_set_attr)
    - [packetbuf_attr](#packetbuf_attr)
    - [packetbuf_set_addr](#packetbuf_set_addr)
    - [packetbuf_addr](#packetbuf_addr)

<!--more-->

# 属性的类型
属性是一个抽象的概念，其本质是一个枚举变量。uIP 协议栈所支持的属性定义如下：
```
enum {
  PACKETBUF_ATTR_NONE,

  /* Scope 0 attributes: used only on the local node. */
  PACKETBUF_ATTR_CHANNEL,
  PACKETBUF_ATTR_NETWORK_ID,
  PACKETBUF_ATTR_LINK_QUALITY,
  PACKETBUF_ATTR_RSSI,
  PACKETBUF_ATTR_TIMESTAMP,
  PACKETBUF_ATTR_RADIO_TXPOWER,
  PACKETBUF_ATTR_LISTEN_TIME,
  PACKETBUF_ATTR_TRANSMIT_TIME,
  PACKETBUF_ATTR_MAX_MAC_TRANSMISSIONS,
  PACKETBUF_ATTR_MAC_SEQNO,
  PACKETBUF_ATTR_MAC_ACK,
  PACKETBUF_ATTR_IS_CREATED_AND_SECURED,

  /* Scope 1 attributes: used between two neighbors only. */
  PACKETBUF_ATTR_RELIABLE,
  PACKETBUF_ATTR_PACKET_ID,
  PACKETBUF_ATTR_PACKET_TYPE,
#if NETSTACK_CONF_WITH_RIME
  PACKETBUF_ATTR_REXMIT,
  PACKETBUF_ATTR_MAX_REXMIT,
  PACKETBUF_ATTR_NUM_REXMIT,
#endif /* NETSTACK_CONF_WITH_RIME */
  PACKETBUF_ATTR_PENDING,
  PACKETBUF_ATTR_FRAME_TYPE,
#if LLSEC802154_SECURITY_LEVEL
  PACKETBUF_ATTR_SECURITY_LEVEL,
  PACKETBUF_ATTR_FRAME_COUNTER_BYTES_0_1,
  PACKETBUF_ATTR_FRAME_COUNTER_BYTES_2_3,
#if LLSEC802154_USES_EXPLICIT_KEYS
  PACKETBUF_ATTR_KEY_ID_MODE,
  PACKETBUF_ATTR_KEY_INDEX,
  PACKETBUF_ATTR_KEY_SOURCE_BYTES_0_1,
#endif /* LLSEC802154_USES_EXPLICIT_KEYS */
#endif /* LLSEC802154_SECURITY_LEVEL */

  /* Scope 2 attributes: used between end-to-end nodes. */
#if NETSTACK_CONF_WITH_RIME
  PACKETBUF_ATTR_HOPS,
  PACKETBUF_ATTR_TTL,
  PACKETBUF_ATTR_EPACKET_ID,
  PACKETBUF_ATTR_EPACKET_TYPE,
  PACKETBUF_ATTR_ERELIABLE,
#endif /* NETSTACK_CONF_WITH_RIME */

  /* These must be last */
  // 地址相关的属性
  PACKETBUF_ADDR_SENDER,
  PACKETBUF_ADDR_RECEIVER,
#if NETSTACK_CONF_WITH_RIME
  PACKETBUF_ADDR_ESENDER,
  PACKETBUF_ADDR_ERECEIVER,
#endif /* NETSTACK_CONF_WITH_RIME */

  // 最后们这个是一个标记，表示所支持的最大的属性。
  PACKETBUF_ATTR_MAX
};

/* Define surrogates when 802.15.4 security is off */
#if !LLSEC802154_SECURITY_LEVEL
enum {
  PACKETBUF_ATTR_SECURITY_LEVEL,
  PACKETBUF_ATTR_FRAME_COUNTER_BYTES_0_1,
  PACKETBUF_ATTR_FRAME_COUNTER_BYTES_2_3
};
#endif /* LLSEC802154_SECURITY_LEVEL */

/* Define surrogates when not using explicit keys */
#if !LLSEC802154_USES_EXPLICIT_KEYS
enum {
  PACKETBUF_ATTR_KEY_ID_MODE,
  PACKETBUF_ATTR_KEY_INDEX,
  PACKETBUF_ATTR_KEY_SOURCE_BYTES_0_1
};
#endif /* LLSEC802154_USES_EXPLICIT_KEYS */
```

我们可以将上面定义的属性分为两类：
- 以 PACKETBUF_ATTR_ 为前缀所表示的属性
- 以 PACKETBUF_ADDR_ 为前缀所表示的属性

为了描述方便，我们将前者叫做 ATTR 属性，将后者叫做 ADDR 属性。

上面定义的属性中，有多少各 ATTR 属性，多少个 ADDR 属性呢？看下面的宏：
```
#if NETSTACK_CONF_WITH_RIME
#define PACKETBUF_NUM_ADDRS 4
#else /* NETSTACK_CONF_WITH_RIME */
#define PACKETBUF_NUM_ADDRS 2
#endif /* NETSTACK_CONF_WITH_RIME */

#define PACKETBUF_NUM_ATTRS (PACKETBUF_ATTR_MAX - PACKETBUF_NUM_ADDRS)
```
即 PACKETBUF_NUM_ADDRS 表示 ADDR 属性的个数，PACKETBUF_NUM_ATTRS 表示 ATTR 属性的个数

# 属性的定义
## ATTR 属性
结构体 struct packetbuf_attr 用于描述一个属性：
```
struct packetbuf_attr {
  packetbuf_attr_t val; // 一个16位无符号整型
};
```
而 packetbuf_attr_t 的定义如下：
```
typedef uint16_t packetbuf_attr_t;
```
由此可见，ATTR 属性的本质就是一个 16 位的无符号整数。

## ADDR 属性
结构体 struct packetbuf_addr 用于描述一个 ADDR 属性：
```
struct packetbuf_addr {
  linkaddr_t addr;
};
```
linkaddr_t 的定义如下：
```
typedef union {
  unsigned char u8[8];  // 一共 8x8=64 bit
  uint16_t u16;         // 一共 16 bit
} linkaddr_t;
```
它是一个联合体，表示 IEEE 802.15.4 所定义的设备的地址：
- 16 bit 的短地址
- 64 bit 的扩展地址 

# l2 buf 中定义的属性
在 struct l2_buf 里面，有两个属性数组：
```
struct l2_buf {
  ...
	struct packetbuf_attr pkt_packetbuf_attrs[PACKETBUF_NUM_ATTRS];
	struct packetbuf_addr pkt_packetbuf_addrs[PACKETBUF_NUM_ADDRS];
  ...
};
```
由于属性的本质是一个枚举变量，这个变量可以充当数组的索引，因此我们可以直接通过访问/设置数据中的对应元素来访问/设置该属性的值。例如：
- pkt_packetbuf_attrs[PACKETBUF_ATTR_CHANNEL] = 3 表示设置 PACKETBUF_ATTR_CHANNEL 属性的值为 3；
- uint16_t val = pkt_packetbuf_attrs[PACKETBUF_ATTR_CHANNEL] 表示将 PACKETBUF_ATTR_CHANNEL 属性的值取出来放到变量 val 里面；

# 访问 l2 buf 中的属性
Zephyr OS 为我们定义了两个宏，可以直接用于访问 l2 buf 里面定义的两个属性数组：
```
#define uip_pkt_packetbuf_attrs(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_packetbuf_attrs)
#define uip_pkt_packetbuf_addrs(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_packetbuf_addrs)
```
# 相关函数
## packetbuf_attr_clear
```
void packetbuf_attr_clear(struct net_buf *buf)
{
  int i;
  for(i = 0; i < PACKETBUF_NUM_ATTRS; ++i) {
    uip_pkt_packetbuf_attrs(buf)[i].val = 0;
  }
  for(i = 0; i < PACKETBUF_NUM_ADDRS; ++i) {
    linkaddr_copy(&uip_pkt_packetbuf_addrs(buf)[i].addr, &linkaddr_null);
  }
}
```
清空两个属性数组的值。
## packetbuf_attr_copyto

```
void packetbuf_attr_copyto(struct net_buf *buf, struct packetbuf_attr *attrs,
		    struct packetbuf_addr *addrs)
{
  memcpy(attrs, uip_pkt_packetbuf_attrs(buf), sizeof(uip_pkt_packetbuf_attrs(buf)));
  memcpy(addrs, uip_pkt_packetbuf_addrs(buf), sizeof(uip_pkt_packetbuf_addrs(buf)));
}
```
将 buf 中的两个属性数组拷贝给 attrs 和 addrs 所指向的内存空间。
## packetbuf_attr_copyfrom

```
void packetbuf_attr_copyfrom(struct net_buf *buf, struct packetbuf_attr *attrs,
		      struct packetbuf_addr *addrs)
{
  memcpy(uip_pkt_packetbuf_attrs(buf), attrs, sizeof(uip_pkt_packetbuf_attrs(buf)));
  memcpy(uip_pkt_packetbuf_addrs(buf), addrs, sizeof(uip_pkt_packetbuf_addrs(buf)));
}
```
将 attrs 和 addrs 所表示的属性拷贝到 buf 中的属性数组中。
## packetbuf_set_attr
```
int packetbuf_set_attr(struct net_buf *buf, uint8_t type, const packetbuf_attr_t val)
{
  uip_pkt_packetbuf_attrs(buf)[type].val = val;
  return 1;
}
```
设置 ATTR 属性数组中的某个属性的值。
## packetbuf_attr

```
packetbuf_attr_t packetbuf_attr(struct net_buf *buf, uint8_t type)
{
  return uip_pkt_packetbuf_attrs(buf)[type].val;
}
```
获取 ATTR 属性数组中某个属性的值。
## packetbuf_set_addr
```
int packetbuf_set_addr(struct net_buf *buf, uint8_t type, const linkaddr_t *addr)
{
  linkaddr_copy(&uip_pkt_packetbuf_addrs(buf)[type - PACKETBUF_ADDR_FIRST].addr, addr);
  return 1;
}
```
设置 ADDR 属性数组中某个属性的地址。
## packetbuf_addr

```
const linkaddr_t *packetbuf_addr(struct net_buf *buf, uint8_t type)
{
  return &uip_pkt_packetbuf_addrs(buf)[type - PACKETBUF_ADDR_FIRST].addr;
}
```
获取 ADDR 属性数组中某个属性的地址。



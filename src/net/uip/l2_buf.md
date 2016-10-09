---
title: Zephys OS uIP 协议栈：L2 buffer - 内存模型
date: 2016-10-09 15:32:13
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Zephyr OS 对 L2(Lay 2,即 MAC 层)定义了一套缓冲管理的模型，相关代码位于`net/ip/l2_buf.c`和`include/net/l2_buf.h`。

- [L2 Buffer 的结构体](#l2-buffer-的结构体)
- [L2 Buffer 的定义](#l2-buffer-的定义)
- [访问 struct l2_buf 的成员](#访问-struct-l2_buf-的成员)
- [L2 Buffer 的内存模型](#l2-buffer-的内存模型)


<!--more-->

# L2 Buffer 的结构体
```
struct l2_buf {
	uint8_t *packetbuf_ptr;
	uint8_t packetbuf_hdr_len;
	uint8_t packetbuf_payload_len;
	uint8_t uncomp_hdr_len;
	int last_tx_status;
#if defined(CONFIG_NETWORKING_WITH_15_4)
	LIST_STRUCT(neighbor_list);
#endif

	struct packetbuf_attr pkt_packetbuf_attrs[PACKETBUF_NUM_ATTRS];
	struct packetbuf_addr pkt_packetbuf_addrs[PACKETBUF_NUM_ADDRS];
	uint16_t pkt_buflen, pkt_bufptr;
	uint8_t pkt_hdrptr;
	uint8_t *pkt_packetbufptr;
};
```
额，定义了一堆一看就乱七八糟的东西，额额，我们瞅一眼后直接略过，因为我们不会直接用来这些成员。

# L2 Buffer 的定义
```
static NET_BUF_POOL(l2_buffers, NET_NUM_L2_BUFS, NET_L2_BUF_MAX_SIZE, \
		    &free_l2_bufs, free_l2_bufs_func, \
		    sizeof(struct l2_buf));
```

回忆一下 NET_BUF_POOL() 的定义：
```
#define NET_BUF_POOL(_name, _count, _size, _fifo, _destroy, _ud_size)	\
	struct {							\
		struct net_buf buf;					\
		uint8_t data[_size] __net_buf_align;	                \
		uint8_t ud[ROUND_UP(_ud_size, 4)] __net_buf_align;	\
	} _name[_count] = {						\
		[0 ... (_count - 1)] = { .buf = {			\
			.user_data_size = ROUND_UP(_ud_size, 4),	\
			.free = _fifo,					\
			.destroy = _destroy,				\
			.size = _size } },			        \
	}
```
我们可以发现 l2_buf 和前面学习的完整版 Buffer 的关系。上面的代码定义了一个缓冲池，缓冲池的名字叫做 l2_buf，它是一个长度为16(NET_NUM_L2_BUFS)的数组，即这个缓冲池里面有 16 个 buffer。对于每一个 buffer，它的内存包含三部分：
- 该 buffer 的控制结构信息区
- 该 buffer 的 data 区
- 该 buffer 的 user data 区

看上面传入的最后一个参数，sizeof(struct l2_buf)，它表示每个 buffer 中用户数据区的长度。因此，我们可以断定：每个 buffer 的用户数据取存放的是 struct l2_buf 类型的变量。

# 访问 struct l2_buf 的成员
Zephyr OS 定义了一套宏，用于访问一个 net buf 中存放的 struct l2_buf 里的各成员：
```
#define uip_packetbuf_ptr(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->packetbuf_ptr)
#define uip_packetbuf_hdr_len(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->packetbuf_hdr_len)
#define uip_packetbuf_payload_len(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->packetbuf_payload_len)
#define uip_uncomp_hdr_len(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->uncomp_hdr_len)
#define uip_last_tx_status(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->last_tx_status)
#if defined(CONFIG_NETWORKING_WITH_15_4)
#define uip_neighbor_list(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->neighbor_list)
#endif
#define uip_pkt_buflen(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_buflen)
#define uip_pkt_bufptr(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_bufptr)
#define uip_pkt_hdrptr(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_hdrptr)
#define uip_pkt_packetbufptr(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_packetbufptr)
#define uip_pkt_packetbuf_attrs(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_packetbuf_attrs)
#define uip_pkt_packetbuf_addrs(buf) \
	(((struct l2_buf *)net_buf_user_data((buf)))->pkt_packetbuf_addrs)
```

这么大一堆，看着就头晕。这些宏怎么使用，留着到下一节再学习，因为太！复！杂！了！

# L2 Buffer 的内存模型

前面我们已经大致知道 L2 Buffer 的内存模型了，即它是一个 net buf 的用户数据。直接上图

<center>

![](/images/zephyr/net/uip/l2/1.png)

图：L2 Buffer 的内存模型
</center>




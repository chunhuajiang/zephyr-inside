---
title: Zephyr OS 网络篇： 缓冲 Buffer 管理 - 简化版
date: 2016-08-23 21:21:23
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本文介绍 Zephyr OS 中的简化版网络 Buffer。

<!--more-->

# 引言
从广义的角度来讲，互联的设备就是一个网络。基于这个概念，Zephyr OS 将网络分为两大类：由 IP 协议构成的网络；由低功耗蓝牙协议构成的网络。二者均位于`net`目录下。

Zephyr OS 中的 IP 网络和蓝牙网络共用同一套 Buffer 模型。

Zephyr OS 中的 Buffer 分为两类，分别是简化版 Buffer 和完整版 Buffer。我们先学习简化版 Buffer。

相关代码位于`include/buf.h`和`net/buf.c`。
# Buffer 的定义
简化版 Buffer 的定义如下：
```
struct net_buf_simple {
	uint8_t *data;
	uint16_t len;
	const uint16_t size;
	uint8_t __buf[0] __net_buf_align;
};
```
主要包含四个成员：
- data：指向buffer中数据部分的起始地址。
- len：buffer中已存储数据的长度，单位是字节。
- size：buffer总共允许存储的数据的长度，单位是字节。
- \__buf：存储数据的起始地址。

> data 和 __buf 都指向数据部分的起始地址，但是它们可能不同。

还有一点需要注意，\__buf[0] 是一个数组，其数组元素个数为 0，这样的数组又叫做柔性数组，用来表示元素个数不确定的数组。柔性数组只能出现在结构体中，其数组长度为 0，我们可以将其看做是数组中的占位符。

此外，Zephyr OS 还提供了一个宏。在编写代码时，我们应该使用该宏来定义一个简单buffer。
```
#define NET_BUF_SIMPLE(_size)                        \
	((struct net_buf_simple *)(&(struct {        \
		struct net_buf_simple buf;           \
		uint8_t data[_size] __net_buf_align; \
	}) {                                         \
		.buf.size = _size,                   \
	}))
```
这是一个比较复杂的、少见的但却非常巧妙的宏，我们逐步分解。
- 先定义了一个匿名结构体：

```
struct {        \
		struct net_buf_simple buf;           \
		uint8_t data[_size] __net_buf_align; \
	}
```
该匿名结构体包含两个元素，一个是 strcut net_buf_simple，另一个是长度为 _size 的数组。我们需要关注它们在内存中的存储情况（将 struct net_buf_simple “展开”）：先存储 data 指针，然后依次存储 len、size 和 data[_size]。

- 再通过符合“&”获取该匿名结构体的地址

```
&(struct {        \
		struct net_buf_simple buf;           \
		uint8_t data[_size] __net_buf_align; \
	})
```
- 再将该匿名结构体的 buf 成员的 size 成员赋值为 _size。

```
(&(struct {        \
		struct net_buf_simple buf;           \
		uint8_t data[_size] __net_buf_align; \
	}) {                                         \
		.buf.size = _size,                   \
	})
```

- 最后再将该匿名结构体的地址强制转化为 struct net_buf_simple * 类型的指针

```
	((struct net_buf_simple *)(&(struct {        \
		struct net_buf_simple buf;           \
		uint8_t data[_size] __net_buf_align; \
	}) {                                         \
		.buf.size = _size,                   \
	}))
```

举个例子，我们进行如下定义：
```
struct net_buf_simple *my_buf = NET_BUF_SIMPLE(10);
```
那么它所做之事就是：分配一片存储空间，将该空间的起始地址赋值给指针 my_buf, 该存储空间依次存储指向实际数据的指针 data、已使用 buffer 长度 len、buffer 可容纳数据的总长度 size 和实际待存储的数据 data[10]。

# Buffer 的初始化

简化版 Buffer 初始化函数如下：
```
static inline void net_buf_simple_init(struct net_buf_simple *buf,
				       size_t reserve_head)
{
	// 将 data 指针指向数据（不包含数据的保留头）的首地址
	buf->data = buf->__buf + reserve_head;
    // 初始化已使用数据（不包含数据的保留头）的长度为 0。
	buf->len = 0;
}
```
有两个参数：
- buf：一个指向需要初始化的 buffer 的指针。
- reserve_head：由于特定场景的保留头部的大小。

在实际编写代码时，**Buffer 的定义和初始化必须配套使用**，例如：
```
struct net_buf_simple *my_buf;

// 定义一个简单buffer，其容量为 10 字节
my_buf = NET_BUF_SIMPLE(10);
// 初始化这个buffer，将其前 2 个字节作为保留的头部。剩下的 8 字节由于存放实际的数据
net_buf_simple_init(my_buf, 2);
```
# Buffer 的内存模型
通过上面的分析，可以抽象出简化版 Buffer 的模型，用一张图表示。

<center>

![](buffer-simply-module.png)

图：简化版 Buffer 的内存模型

> 未考虑内存对齐问题

</center>

主要关注以下要点：

- 存储的顺序依次为描述 buffer 的结构体中各成员、buffer 的数据
- 描述 buffer 的结构体中各成员的含义
  - 指针 data 指向已使用 buffer 的首地址
  - len 表示已使用 buffer 的长度，单位是字节
  - size 表示 buffer 的总长度，单位是字节
  - __buf 指向 buffer 的保留头部的首地址，即 data[0] 的地址
- buffer 的数据由三部分组成：
  - 保留的头部(如果存在)，即 reserved_head 所表示的空间
  - 已使用buffer，即 len 所表示的空间
  - 未使用buffer，即 tailroom 所表示的空间
- 数据部分可能有保留头部(reserved_head > 0)，也可能没有保留头部(reserved_head = 0)

# Buffer 的接口

## net_buf_simple_tail

```
static inline uint8_t *net_buf_simple_tail(struct net_buf_simple *buf)
{
	return buf->data + buf->len;
}
```

获取并返回 buffer 的尾部(未使用部分)的首地址

##  net_buf_simple_headroom

```
size_t net_buf_simple_headroom(struct net_buf_simple *buf)
{
	return buf->data - buf->__buf;
}
```

获取并返回 buffer 的头部的大小

## net_buf_simple_tailroom

```
size_t net_buf_simple_tailroom(struct net_buf_simple *buf)
{
	return buf->size - net_buf_simple_headroom(buf) - buf->len;
}
```

获取并返回 buffer 的尾部(未使用空间)的大小

## net_buf_simple_add

```c
void *net_buf_simple_add(struct net_buf_simple *buf, size_t len)
{
	uint8_t *tail = net_buf_simple_tail(buf);

	NET_BUF_ASSERT(net_buf_simple_tailroom(buf) >= len);

	buf->len += len;
	return tail;
}
```

向 buffer 中添加数据前的相关工作：

- 判断 buf 是否还有足够的空间来保存 len 个字节的数据。
- 将 buf 中的 len 预增加
- 返回未使用部分的首地址

> 这个函数存在一个安全隐患。NET_BUF_ASSERT 将判断条件 net_buf_simple_tailroom(buf) >= len 是否正确，如果不正确，即 len 大于 buffer 中未使用部分的空间，它仅仅打印一条提示消息。也就是说，如果条件不正确，那么向该 buf 中添加数据时将导致缓冲越界！一个很严重的错误！！

### net_buf_simple_add_u8

```
uint8_t *net_buf_simple_add_u8(struct net_buf_simple *buf, uint8_t val)
{
	uint8_t *u8;

	u8 = net_buf_simple_add(buf, 1);
	*u8 = val;

	return u8;
}
```

向 buf 中添加 1 个字节的无符号整形数据。

### net_buf_simple_add_le16

```
void net_buf_simple_add_le16(struct net_buf_simple *buf, uint16_t val)
{
	val = sys_cpu_to_le16(val);
	memcpy(net_buf_simple_add(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 中添加 2 个字节的 unsigned short 类型的数据，且该数据在 buf 中以小端的格式存储。

###  net_buf_simple_add_be16

```
void net_buf_simple_add_be16(struct net_buf_simple *buf, uint16_t val)
{
	NET_BUF_DBG("buf %p val %u\n", buf, val);

	val = sys_cpu_to_be16(val);
	memcpy(net_buf_simple_add(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 中添加 2 个字节的 unsigned short 类型的数据，且该数据在 buf 中以大端的格式存储。

### net_buf_simple_add_le32

```
void net_buf_simple_add_le32(struct net_buf_simple *buf, uint32_t val)
{
	val = sys_cpu_to_le32(val);
	memcpy(net_buf_simple_add(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 中添加 4 个字节的 unsigned int类型的数据，且该数据在 buf 中以小端的格式存储。

###  net_buf_simple_add_be32

```
void net_buf_simple_add_be32(struct net_buf_simple *buf, uint32_t val)
{
	val = sys_cpu_to_be32(val);
	memcpy(net_buf_simple_add(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 中添加 4 个字节的 unsigned int类型的数据，且该数据在 buf 中以大端的格式存储。

## net_buf_simple_push

```
void *net_buf_simple_push(struct net_buf_simple *buf, size_t len)
{
	NET_BUF_ASSERT(net_buf_simple_headroom(buf) >= len);

	buf->data -= len;
	buf->len += len;
	return buf->data;
}
```

该函数也是为向buf添加数据做准备工作，但与 net_buf_simple_add 不同的是，使用 push 添加数据时是将数据添加到 buf 中已使用数据的前面(即 reserved_head 中)，使用add 添加数据时是将数据添加到 buf 中已使用数据的后面(即 buf 的未使用部分)。

所做的准备工作：

- 判断头部空间是否足够用来存储 len 个字节
- 将 data 指针前移 len 字节
- 将 buf 中的 len 预增加

> 同样地，也可能造成缓冲溢出

### net_buf_simple_push_u8

```
void net_buf_simple_push_u8(struct net_buf_simple *buf, uint8_t val)
{
	uint8_t *data = net_buf_simple_push(buf, 1);

	*data = val;
}
```

向 buf 的头部中添加 1 个字节的 unsigned char 类型的数据。

### net_buf_simple_push_le16

```
void net_buf_simple_push_le16(struct net_buf_simple *buf, uint16_t val)
{
	val = sys_cpu_to_le16(val);
	memcpy(net_buf_simple_push(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 的头部添加 2 个字节的 unsigned short 类型的数据，且该数据在 buf 中以小端的格式存储。

### net_buf_simple_push_le16

```
void net_buf_simple_push_be16(struct net_buf_simple *buf, uint16_t val)
{
	val = sys_cpu_to_be16(val);
	memcpy(net_buf_simple_push(buf, sizeof(val)), &val, sizeof(val));
}
```

向 buf 的头部添加 2 个字节的 unsigned short 类型的数据，且该数据在 buf 中以大端的格式存储。

## net_buf_simple_pull

```
void *net_buf_simple_pull(struct net_buf_simple *buf, size_t len)
{
	NET_BUF_ASSERT(buf->len >= len);

	buf->len -= len;
	return buf->data += len;
}
```

从 buf 中取出数据后的收尾工作，包括：

- 判断 buf 中数据的长度大于 len
- buf 的 len 减小
- buf 的 data 指针后移 len

### net_buf_simple_pull_u8

```
uint8_t net_buf_simple_pull_u8(struct net_buf_simple *buf)
{
	uint8_t val;

	val = buf->data[0]; // 先取出数据
	net_buf_simple_pull(buf, 1); // 再处理 len, data 指针

	return val;
}
```

从 buf 中的有效数据的首地址取出 1 个字节并返回。

### net_buf_simple_pull_le16

```
uint16_t net_buf_simple_pull_le16(struct net_buf_simple *buf)
{
	uint16_t val;

	val = UNALIGNED_GET((uint16_t *)buf->data);
	net_buf_simple_pull(buf, sizeof(val));

	return sys_le16_to_cpu(val);
}
```

从 buf 中的有效数据的首地址处按小端的方式取出 2 字节构成一个 unsigned short 类型的数据并返回。

### net_buf_simple_pull_be16

```
uint16_t net_buf_simple_pull_be16(struct net_buf_simple *buf)
{
	uint16_t val;

	val = UNALIGNED_GET((uint16_t *)buf->data);
	net_buf_simple_pull(buf, sizeof(val));

	return sys_be16_to_cpu(val);
}
```

从 buf 中的有效数据的首地址处按大端的方式取出 1 字节构成一个 unsigned short 类型的数据并返回。

### net_buf_simple_pull_le32

```
uint32_t net_buf_simple_pull_le32(struct net_buf_simple *buf)
{
	uint32_t val;

	val = UNALIGNED_GET((uint32_t *)buf->data);
	net_buf_simple_pull(buf, sizeof(val));

	return sys_le32_to_cpu(val);
}
```

从 buf 中的有效数据的首地址处按小端的方式取出 4 字节构成一个 unsigned int 类型的数据并返回

### net_buf_simple_pull_be32

```
uint32_t net_buf_simple_pull_be32(struct net_buf_simple *buf)
{
	uint32_t val;

	val = UNALIGNED_GET((uint32_t *)buf->data);
	net_buf_simple_pull(buf, sizeof(val));

	return sys_be32_to_cpu(val);
}
```

# 总结

简化版 Buffer 的模型设计得很不好，一不小心就可能造成缓冲溢出，因此在使用这些接口是一定要小心。

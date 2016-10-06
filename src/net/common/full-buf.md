---
title: Zephys OS 网络篇：缓冲池 - 完整版 Buffer
date: 2016-10-06 20:54:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---
介绍完整版的缓冲池。

- [Buffer 的结构体](#buffer-的结构体)
- [Buffer 的定义](#buffer-的定义)
- [Buffer 的初始化](#buffer-的初始化)
- [将 Buffer 放到 fifo 中](#将-buffer-放到-fifo-中)
- [从 fifo 中取出 Buffer](#从-fifo-中取出-buffer)
- [增加 Buffer 的引用计数](#增加-buffer-的引用计数)
- [减小 Buffer 的引用计数](#减小-buffer-的引用计数)
- [其它 API](#其它-api)

<!--more-->
# Buffer 的结构体
```
struct net_buf {
	union {
		int _unused;
        // 如果本 buffer 是一个原始报文的分片，且不是最后一个分片，则 frags 指向下
        // 一个分片(即分配的 buffer)
		struct net_buf *frags;
	};
	// 该 buffer 所关联的用户数据的尺寸
	const uint16_t user_data_size;
    // 该 buffer 的引用计数
	uint8_t ref;
    // 标志当前 buf 是否还有后续分片
	uint8_t flags;
    // !! 每个 Buffer 绑定了一个 fifo，即这里点 fifo 成员 !!
    // !! free 是 Buffer 中的一个很关键的成员 !!
	struct nano_fifo * const free;
    // 一个回调函数的指针。当该 buffer 被释放时，会调用该函数。
	void (*const destroy)(struct net_buf *buf);

	union {
    	// 这个结构体里面的内容必须与 net_buf_simple 里面的内容匹配
		struct {
        	// 指向该 buffer 中实际存放的数据的起始。可能对于 __buf[0]，
            // 也可能不等于 __buf[0]
			uint8_t *data;
            // 该 buffer 中已存放的数据的长度
			uint16_t len;
            // 该 buffer 的容量
			const uint16_t size;
		};
		struct net_buf_simple b;
	};
    // 存储数据的空间的起始地址。
	uint8_t __buf[0] __net_buf_align;
};
```
frags 和 flags 都可用于表示当前 buffer 是否还有后续分片，它们的区别在后面有说明。

# Buffer 的定义

Buffer 的定义必须使用宏 NET_BUF_POOL()：
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
上面的代码定义了一个匿名结构体，该结构体包含三部分：
- buf：用于描述一个 buffer 的结构体。
- data：用于存放实际数据的一段 buffer 空间。
- ud：用来存放用户数据的一段 buffer 空间。

然后使用该匿名结构体定义了一组 buffer，即一个数组变量，并对该数组变量中各元素的结构体成员进行了初始化。

- _name: buffer(数组变量)的名字。
- _count: buffer 的个数(即数组的长度)。
- _size: 每个 buffer 的数据存储容量。
- _fifo: buffer 被释放时需要指向的 fifo。
- _destroy: buffer 被释放时需要被调用的回调函数。
- _ud_size: 用户空间的大小。

有一点需要特别关注，即每个 buffer 的 free 成员所指向的 fifo 是同一个 fifo。也就是说，使用 NET_BUF_POOL 所定义的一组 Buffer 被绑定到一个 fifo 上面。

从这个初始化宏，我们可以总结出完整版 Buffer 的内存模型：

<center>
![](full_buf.png)

图：完整版 Buffer 的内存模型
</center>

# Buffer 的初始化
```
#define net_buf_pool_init(pool)						\
	do {								\
		int i;							\
									\
		nano_fifo_init(pool[0].buf.free);			\
									\
		for (i = 0; i < ARRAY_SIZE(pool); i++) {		\
			nano_fifo_put(pool[i].buf.free, &pool[i]);	\
		}							\
	} while (0)
```
它先初始化了 buffer 的 free 所指向的 fifo(使用 NET_BUF_POOL 所定义的一组 buffer 指向同一个 fifo)，然后将每个 buffer 依次添加到该 fifo 中。

# 将 Buffer 放到 fifo 中
```
void net_buf_put(struct nano_fifo *fifo, struct net_buf *buf)
{
	struct net_buf *tail;

	for (tail = buf; tail->frags; tail = tail->frags) {
    	// 如果这个 buf 有分片，则将该 buf 以及后续分片 buf 的 flag 标
        // 记为 NET_BUF_FRAGS
		tail->flags |= NET_BUF_FRAGS;
	}
	
    // 将该 buf (以及后续分片)放入 fifo 中
	nano_fifo_put_list(fifo, buf, tail);
}
```
# 从 fifo 中取出 Buffer
函数 net_buf_get 可用于从 fifo 中取出 buffer：
```
struct net_buf *net_buf_get(struct nano_fifo *fifo, size_t reserve_head)
{
	struct net_buf *buf;

	// net_buf_get_timeout 会根据第三个参数调用对应的 fifo 函数，这里
    // 传入的参数是 TICKS_NONE，表示无论在 fifo 中有没有获取到 buffer，
    // 都立即返回。
	buf = net_buf_get_timeout(fifo, reserve_head, TICKS_NONE);
	if (buf || sys_execution_context_type_get() == NANO_CTX_ISR) {
    	// 如果获取到了 buf，立即返回；
        // 如果没有获取到 buf，但是当前上下文是 ISR，也立即返回
		return buf;
	}
	
	// 代码走到这里，说明刚才没有获取到 buf，且当前上下文不是 ISR，那么再次调用
    // 函数 net_buf_get_timeout 获取 buf，但是此次传入的参数是 TICKS_UNLIMITED，
    // 表示如果 fifo 中没有 buf，就陷入阻塞状态，一直等待，直到有 buf 被放入到
    // 该 fifo 中，然后取出该 buf 并返回。
	return net_buf_get_timeout(fifo, reserve_head, TICKS_UNLIMITED);
}
```
下面再分析net_buf_get_timeout：
```
struct net_buf *net_buf_get_timeout(struct nano_fifo *fifo,
				    size_t reserve_head, int32_t timeout)
{
	struct net_buf *buf, *frag;

	buf = nano_fifo_get(fifo, timeout);
	if (!buf) {
		NET_BUF_ERR("Failed to get free buffer\n");
		return NULL;
	}

	// 代码走到这里，说明取到了 buf
    
	/* If this buffer is from the free buffers FIFO there wont be
	 * any fragments and we can directly proceed with initializing
	 * and returning it.
	 */
	if (buf->free == fifo) {
    	// 为什么这里表示该 buf 没有后续分片了 ？
		buf->ref   = 1;
		buf->len   = 0;
		net_buf_reserve(buf, reserve_head);
		buf->flags = 0;
		buf->frags = NULL;

		return buf;
	}

	// 将该 buf 的所有后续分片从 fifo 中移除。
	for (frag = buf; (frag->flags & NET_BUF_FRAGS); frag = frag->frags) {
		frag->frags = nano_fifo_get(fifo, TICKS_NONE);
		NET_BUF_ASSERT(frag->frags);

		// 因为该标志只在 fifo 中有用。当 buf 从该 fifo 中取出后，可以根据 frags 是否
        // 为空表示该 buf 是否还有后续分片。所以这里将分片标志清楚了。
		frag->flags &= ~NET_BUF_FRAGS;
	}

    // 将从 fifo 中取出了最后一个分片的 frags 设置 NULL，作为 buf 是否还有后续分片的判断
	frag->frags = NULL;

	return buf;
}
```
# 增加 Buffer 的引用计数
```
struct net_buf *net_buf_ref(struct net_buf *buf)
{
	buf->ref++;
	return buf;
}
```
# 减小 Buffer 的引用计数
```
void net_buf_unref(struct net_buf *buf)
{
	NET_BUF_ASSERT(buf->ref > 0);

	while (buf && --buf->ref == 0) {
		struct net_buf *frags = buf->frags;

		buf->frags = NULL;

		if (buf->destroy) {
			buf->destroy(buf);
		} else {
			nano_fifo_put(buf->free, buf);
		}

		buf = frags;
	}
}
```
先对 buf 的引用计数减 1，然后判断引用计数是否为 0：
- 如果不为 0，直接返回；
- 如果为 0，
  - 如果该 buf 绑定了 destroy 函数，调用该函数。
  - 如果该 buf 没绑定 destroy 函数，将该 buf 添加到 fifo 中取。

如果该 buf 有后续分片，则重复上面的故事。
# 其它 API
克隆一个 buf：
- struct net_buf *net_buf_clone(struct net_buf *buf)

获取 buf 的用户数据：
- static inline void *net_buf_user_data(struct net_buf *buf)

向 buf 的尾部添加数据：
- net_buf_add(buf, len)
- net_buf_add_u8(buf, val)
- net_buf_add_le16(buf, val)
- net_buf_add_be16(buf, val)
- net_buf_add_le32(buf, val)
- net_buf_add_be32(buf, val)


向 buf 的头部预留空间添加数据：
- net_buf_push(buf, len)
- net_buf_push_le16(buf, val)
- net_buf_push_be16(buf, val)
- net_buf_push_u8(buf, val)

从 buf 的数据头部取出数据：
- net_buf_pull(buf, len)
- net_buf_pull_u8(buf)
- net_buf_pull_le16(buf)
- net_buf_pull_be16(buf)
- net_buf_pull_le32(buf)
- net_buf_pull_be32(buf)

获取 buf 的尾部的未使用空间的大小：
- net_buf_tailroom(buf)

获取 buf 的头部空间大小：
- net_buf_headroom(buf)

获取 buf 的尾部空间的地址：
- net_buf_tail(buf)

获取 buf 的最后一个分片：
- struct net_buf *net_buf_frag_last(struct net_buf *frags)

向一个 buf 添加一个分片：
- net_buf_frag_add(parent, frag)

删除 buf 的分片：
- void net_buf_frag_del(struct net_buf *parent, struct net_buf *frag)

计算 buf 的所有分片的存储的数据长度：
- static inline size_t net_buf_frags_len(struct net_buf *buf)






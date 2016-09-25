---
title: Zephys OS nano 内核篇：环形缓冲 Ring Buffer
date: 2016-09-25 10:34:45
categories: ["Zephyr OS"]
tags: [Zephyr]
---

与栈有点类似，环形缓冲的大小也是在初始化时就固定了。

# 环形缓冲的类型定义

```
struct ring_buf {
	uint32_t head;	 /**< Index in buf for the head element */
	uint32_t tail;	 /**< Index in buf for the tail element */
	uint32_t dropped_put_count; /**< Running tally of the number of failed put attempts */
	uint32_t size;   /**< Size of buf in 32-bit chunks */
	uint32_t *buf;	 /**< Memory region for stored entries */
	uint32_t mask;   /**< Modulo mask if size is a power of 2 */
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct ring_buf *__next;
#endif
};
```

不考虑用于调试的 __next，环形buffer一个有6个成员：

- head：“指向”环形buffer中数据的头部。注意，head不是指针，而是一个下标索引。
- tail：“指向”环形buffer中数据的尾部的下一个地址。注意，tail也不是指针，是一个下标索引。
- dropped_put_count：记录向buffer中添加数据时由于buffer剩余空间不够而被丢弃的数据的次数。
- size：环形buffer的总容量。
- buf：指向环形buffer的起始地址。
- mask：当buffer的长度是2的整数次幂时，使用该成员进行“取模”运算，将buffer的下标索引表示在(0, size-1)范围内。

# 环形缓冲的初始化

nanokernel 提供了三种初始化环形buffer的方法，它们分别有各自的使用场景

## SYS_RING_BUF_DECLARE_POW2

```
#define SYS_RING_BUF_DECLARE_POW2(name, pow) \
	static uint32_t _ring_buffer_data_##name[1 << (pow)]; \
	struct ring_buf name = { \
		.size = (1 << (pow)), \
		.mask = (1 << (pow)) - 1, \
		.buf = _ring_buffer_data_##name \
	};
```

当buffer的长度是2的整数次幂时，推荐使用该宏进行初始化。当使用该宏进行初始化后，再向该buffer中添加数据和取出数据时的效率比使用第二种方法的效率高。该宏做了两件事儿：

- 先定义了一个buffer，即环形缓冲实际用来存放数据的buffer。
- 定义了一个描述环形缓冲的结构体，并对其相关成员进行初始化。
  - size：初始化为$$2^{pow}$$ 。
  - mask：初始化为二进制的0b111...111，即后面一共有pow个1。
  - buf：指向所分配的内存空间。
  - buffer中其它成员被初始化为 0。

使用该宏进行初始化时，所开辟的buffer的内存空间的长度是$$4*2^{pow}$$字节。

## SYS_RING_BUF_DECLARE_SIZE

```
#define SYS_RING_BUF_DECLARE_SIZE(name, size32) \
	static uint32_t _ring_buffer_data_##name[size32]; \
	struct ring_buf name = { \
		.size = size32, \
		.buf = _ring_buffer_data_##name \
	};
```

当buffer的长度不是2的整数次幂时，可以使用该宏进行初始化。使用该宏初始化后，再向该buffer中添加数据和取出数据时的效率比使用第一种方法的效率低。该宏做了两件事儿：

- 先定义了一个buffer，即环形缓冲实际用来存放数据的buffer。
- 定义了一个描述环形缓冲的结构体，并对其相关成员进行初始化。
  - size：初始化为size32。
  - buf：指向所分配的内存空间。
  - buffer中其它成员被初始化为 0。


使用该宏进行初始化时，所开辟的buffer的内存空间的长度是$$4*size32$$ 。

## sys_ring_buf_init

```
static inline void sys_ring_buf_init(struct ring_buf *buf, uint32_t size,
				     uint32_t *data)
{
	buf->head = 0;
	buf->tail = 0;
	buf->dropped_put_count = 0;
	buf->size = size;
	buf->buf = data;
	// is_power_of_two()用于判断一个数是不是2的整数次幂，其实现非常
	// 巧妙，有兴趣的可以研究研究
	if (is_power_of_two(size)) {
		buf->mask = size - 1;
	} else {
		buf->mask = 0;
	}

	SYS_TRACING_OBJ_INIT(sys_ring_buf, buf);
}
```

该函数能判断buffer的大小是不是2的整数次幂，然后进行相应的初始化。使用该函数进行初始化的一般步骤为：

```
#define MY_RING_BUF_SIZE    64

struct my_struct {
    struct ring_buffer rb;
    uint32_t buffer[MY_RING_BUF_SIZE];
    ...
};
struct my_struct ms;

void init_my_struct {
    sys_ring_buf_init(&ms.rb, sizeof(ms.buffer), ms.buffer);
    ...
}
```



假设我们初始化了一个长度为16的buffer，那么其内存空间分布情况如图 1 所示。

<center>

![](/images/zephyr/kernel/nanokernel/ring_buf/1.png)



图 1. 环形缓冲的内存空间存储情况

</center>

# 添加数据

```
int sys_ring_buf_put(struct ring_buf *buf, uint16_t type, uint8_t value,
		     uint32_t *data, uint8_t size32)
{
	uint32_t i, space, index, rc;

	// 先获取buffer中剩余空间的长度
	space = sys_ring_buf_space_get(buf);
	if (space >= (size32 + 1)) {
		// 如果剩余空间足够存放数据，才将其存放到buffer中
		// 这里判断剩余空间的长度是否大于 size32 + 1，是因为除了真实的数据外，
		// 还有一个数据头(占一个整型的长度)，用于记录数据的 metadata。
		struct ring_element *header =
				(struct ring_element *)&buf->buf[buf->tail];
		header->type = type;
		header->length = size32;
		header->value = value;

		// 通过mask的值是否为0，判断buffer的长度是否是2的整数次幂，然后分开处理
		if (likely(buf->mask)) {
			//　如果是2的整数次幂
			for (i = 0; i < size32; ++i) {
				// 一个字节一个字节地将数据复制到buffer中
				// 先通过与 mask 按位与取得index
				index = (i + buf->tail + 1) & buf->mask;
				// 再复制数据
				buf->buf[index] = data[i];
			}
			//　将tail“指向”数据buffer中数据末尾的下一个地址处
			buf->tail = (buf->tail + size32 + 1) & buf->mask;
		} else {
			// 如果不是2的整数次幂
			for (i = 0; i < size32; ++i) {
				// 一个字节一个字节地将数据复制到buffer中
				// 先通过对 size 进行取模运算取得 index
				index = (i + buf->tail + 1) % buf->size;
				// 再复制数据
				buf->buf[index] = data[i];
			}
			//　将tail“指向”数据buffer中数据末尾的下一个地址处
			buf->tail = (buf->tail + size32 + 1) % buf->size;
		}
		rc = 0;
	} else {
		// 如果buffer的剩余空间不够存放数据，dropped_put_count 递增
		buf->dropped_put_count++;
		// 并返回错误码
		rc = -EMSGSIZE;
	}

	return rc;
} 
```

sys_ring_buf_space_get()用于获取buffer的剩余空间，其实现如下：

```
static inline int sys_ring_buf_space_get(struct ring_buf *buf)
{
	if (sys_ring_buf_is_empty(buf)) {
		// 当buffer为空，参考图1
		return buf->size - 1;
	}
	
	// 当tail < head，参考图 2
	if (buf->tail < buf->head) {
		return buf->head - buf->tail - 1;
	}

	// 当 tail > head，参考图3
	return (buf->size - buf->tail) + buf->head - 1;
}
```

<center>

![](/images/zephyr/kernel/nanokernel/ring_buf/2.png)



图 2. tail < head 的示意图

</center>

<center>

![](/images/zephyr/kernel/nanokernel/ring_buf/3.png)



图 3. tail < head 的示意图

</center>

# 取出数据

```
int sys_ring_buf_get(struct ring_buf *buf, uint16_t *type, uint8_t *value,
		     uint32_t *data, uint8_t *size32)
{
	struct ring_element *header;
	uint32_t i, index;

	if (sys_ring_buf_is_empty(buf)) {
		// 如果 buffer 是空的，直接返回错误码
		return -EAGAIN;
	}

	header = (struct ring_element *) &buf->buf[buf->head];

	if (header->length > *size32) {
		// 数据长度不匹配，将实际长度返回给调用者
		*size32 = header->length;
		// 然后返回错误码
		return -EMSGSIZE;
	}

	*size32 = header->length;
	*type = header->type;
	*value = header->value;

	if (likely(buf->mask)) {
		// 如果 buffer 的长度是 2 的整数次幂
		for (i = 0; i < header->length; ++i) {
			// 通过与 mask 的按位与运算，取得 index
			index = (i + buf->head + 1) & buf->mask;
			// 然后复制数据到 data 中
			data[i] = buf->buf[index];
		}
		// 重新调整头部 index
		buf->head = (buf->head + header->length + 1) & buf->mask;
	} else {
		// 如果 buffer 的长度不是 2 的整数次幂
		for (i = 0; i < header->length; ++i) {
			// 通过与 buffer 的 size 进行取模运算，获取 index
			index = (i + buf->head + 1) % buf->size;
			// 然后复制数据到 data 中
			data[i] = buf->buf[index];
		}
		// 重新调整头部 index
		buf->head = (buf->head + header->length + 1) % buf->size;
	}

	return 0;
}  
```


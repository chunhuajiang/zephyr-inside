---
title: Zephys OS nano内核篇：超时服务timeout
date: 2016-09-09 19:19:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Zephys 的内核大总管 _nanokernel 掌握着一个超时链表(sys_dlist_t timeout_q)，这个链表中的每个节点都绑定了一个超时时间、一个线程和/或一个回调函数。当超时时间到期时，会执行该节点所绑定的线程(将其设为就绪态)或者回调函数。

- [滴答时钟](#滴答时钟)
- [类型定义](#类型定义)
- [_nano_timeout_init](#_nano_timeout_init)
- [_nano_timeout_add](#_nano_timeout_add)
- [_nano_timeout_handle_timeouts](#_nano_timeout_handle_timeouts)
- [_nano_timeout_abort](#_nano_timeout_abort)
- [_nano_get_earliest_timeouts_deadline](#_nano_get_earliest_timeouts_deadline)

<!--more-->
# 滴答时钟

要学习超时服务，必须需要先了解一下滴答时钟的概念。一般而言，一颗 CPU 都至少有两类时钟：
- 高频时钟：系统时钟(system clock)，也叫做主时钟(main clock)。CPU 在每个时钟周期内取值、执行(有些指令可能需要多个时钟周期)。
- 低频时钟：低频时钟可以用作系统的滴答时钟(systick clock)，或者看门狗时钟(WDT clock)等多种用途。例如 TI 的 RF 芯片 CC2538，其滴答时钟是 32 KHz，即在每秒之内将产生 32000 个滴答，每个滴答的周期是 1/32000 秒。

Zephyr OS 中定时器的实现就是利用滴答时钟实现的。超时链表中的节点所绑定的超时时间就是以滴答为单位的。系统每产生一次滴答，都会触发一次滴答中断，从而会调用滴答中断的中断服务例程(ISR)。在这个中断例程中，会先将超时链表中各节点所绑定的超时时间减 1，然后处理该链表中所有超时时间减至 0 的节点(即调用线程或执行回调函数)。更多的知识请参考后续的文章《Zephyr OS 内核篇：定时器Timer》和《Zephyr OS 驱动篇：滴答时钟 SysTick》。

# 类型定义
```
struct _nano_timeout {
	sys_dlist_t node;
	struct tcs *tcs;
	struct _nano_queue *wait_q;
	int32_t delta_ticks_from_prev;
	_nano_timeout_func_t func;
};
```
各成员含义如下：
- node: 描述该节点在超时链表中的位置，可以通过该变量找到本节点的前驱节点和后继节点。
- tcs: 超时节点所绑定的线程。
- wait_q: 超时节点所绑定的等待队列(暂时还不了解有什么作用)。
- delta_ticks_from_prev：超时时间，以系统的滴答(tick)为单位。
- func: 超时节点所绑定的回调函数。

timeout 支持如下 API ：
- **_nano_timeout_init**: 初始化 timeout 中结构体中相关成员。
- **_nano_timeout_add**: 将某个 timeout 加入到 _nanokernel 的超时链表中。
- **_nano_timeout_handle_timeouts**: 处理 _nanokerenl 的超时链表中的所以已超时的节点。
- **_nano_timeout_abort**: 终止某个超时节点，即从超时链表中删除。
- **_nano_get_earliest_timeouts_deadline**：返回即将超时时间即将到期的节点。

# _nano_timeout_init
```
static inline void _nano_timeout_init(struct _nano_timeout *t,
				      _nano_timeout_func_t func)
{
	t->delta_ticks_from_prev = -1;
	t->wait_q = NULL;
	t->tcs = NULL;
	t->func = func;
}
```
初始化超时结构中的各变量。
# _nano_timeout_add
```
static inline void _nano_timeout_add(struct tcs *tcs,
				     struct _nano_queue *wait_q,
				     int32_t timeout)
{
	_do_nano_timeout_add(tcs,  &tcs->nano_timeout, wait_q, timeout);
}
```
继续追踪 _do_nano_timeout_add:
```
void _do_nano_timeout_add(struct tcs *tcs,
					 struct _nano_timeout *t,
				     struct _nano_queue *wait_q,
				     int32_t timeout)
{
	// 获取内核大总管 _nanokernel 的超时链表
	sys_dlist_t *timeout_q = &_nanokernel.timeout_q;

	t->tcs = tcs;	// 绑定本节点线程
	t->delta_ticks_from_prev = timeout;	// 设置本节点的超时时间，以滴答(tick)为单位
	t->wait_q = wait_q; // 绑定本节点等待队列
    // 在超时链表中插入本节点，请看下面的具体分析
	sys_dlist_insert_at(timeout_q, (void *)t,
						_nano_timeout_insert_point_test,
						&t->delta_ticks_from_prev);
}
```

在《Zephyr OS 内核篇： 内核链表》已经讲解了函数 sys_dlist_insert_at()，它会从超时链表的头节点依次测试，直到该节点满足条件 _nano_timeout_insert_point_test()，即该函数的返回值非 0。继续追踪 _nano_timeout_insert_point_test:
```
static int _nano_timeout_insert_point_test(sys_dnode_t *test, void *timeout)
{
	struct _nano_timeout *t = (void *)test;
	int32_t *timeout_to_insert = timeout;

    // 如果待插入的节点的超时时间大于测试节点的增量超时时间，timeout_to_insert 减去测试节点的超
    // 时时间，并返回0，测试下一个节点。
	if (*timeout_to_insert > t->delta_ticks_from_prev) {
		*timeout_to_insert -= t->delta_ticks_from_prev;
		return 0;
	}
	
    // 如果代码走到这里，表示待插入的节点的测试时间小于测试测点，则表示待插入的节点将插入到该
    // 测试节点之前，并将测试节点的超时时间嵌入待插入节点的增量超时时间。
	t->delta_ticks_from_prev -= *timeout_to_insert;
	return 1;
}
```
通过分析函数 _nano_timeout_insert_point_test 内部的代码，我们可以得出如下结论：**内核维持的超时链表，其每个节点所绑定的超时时间是一个增量超时时间，即某节点的实际增量时间等于该节点前面所有节点(包括该节点自己)的超时时间之和**。例如，如果超时链表中有 3 个节点，每个节点所绑定的超时时间分别为 3 ticks、6 ticks、4 ticks，那么每个节点实际将等待的超时时间分别为 3 ticks、9 ticks、13 ticks。

> 还记得高中数学的 Δ 和高等数学中的 δ 这两个符号吗？它们是表示增量的符号。回忆一下它们是怎么发音的，呃，，它们的英文就是 delta。

# _nano_timeout_handle_timeouts
```
void _nano_timeout_handle_timeouts(void)
{
	sys_dlist_t *timeout_q = &_nanokernel.timeout_q;
	struct _nano_timeout *next;

	// 遍历链表中所有超时时间为 0 的所有节点，并依次处理
	next = (struct _nano_timeout *)sys_dlist_peek_head(timeout_q);
	while (next && next->delta_ticks_from_prev == 0) {
		next = _nano_timeout_handle_one_timeout(timeout_q);
	}
}
```
上面的代码很简单。系统在每次滴答时钟到来的时候，会先将超时链表中的所有节点所绑定的超时时间减 1，然后判断头节点的超时时间是否为 0。如果为 0，则会调用本函数处理超时时间为 0 的所有节点。下面继续追踪函数 _nano_timeout_handle_one_timeout()。
```
static struct _nano_timeout *_nano_timeout_handle_one_timeout(
	sys_dlist_t *timeout_q)
{
	// 获取超时队列中的头节点，并将其从超时链表中删除
	struct _nano_timeout *t = (void *)sys_dlist_get(timeout_q);
    // 获取头节点所绑定的线程结构体
	struct tcs *tcs = t->tcs;

	if (tcs != NULL) {
    	// 如果线程结构体不为空，即该节点确实绑定了线程，将该线程从等待队列
        // 中删除(如果该节点绑定了等待队列)。
		_nano_timeout_object_dequeue(tcs, t);
		if (_IS_MICROKERNEL_TASK(tcs)) {
        	// 如果该线程是 task，将其加入 task 的就绪链表中去
			_NANO_TASK_READY(tcs);
		} else {
        	// 如果线程是 fiber，将其加入 fiber 的就绪链表中去
			_nano_fiber_ready(tcs);
		}
	} else if (t->func) {
    	// 如果该节点为绑定线程，但是绑定了回调函数，则执行回调函数
		t->func(t);
	}
	t->delta_ticks_from_prev = -1;

	// 返回下一个节点
	return (struct _nano_timeout *)sys_dlist_peek_head(timeout_q);
}
```
继续追踪函数 _nano_timeout_object_dequeue：
```
static void _nano_timeout_object_dequeue(
	struct tcs *tcs, struct _nano_timeout *t)
{
	if (t->wait_q) {
    	// 如果节点绑定了等待队列，将其从等待队列中删除
		_nano_timeout_remove_tcs_from_wait_q(tcs, t->wait_q);
        // 设置线程 tcs 的返回值为 0。为啥？不知道。。
		fiberRtnValueSet(tcs, 0);
	}
}

static void _nano_timeout_remove_tcs_from_wait_q(
	struct tcs *tcs, struct _nano_queue *wait_q)
{
	if (wait_q->head == tcs) {
    	// 如果该线程是等待队列的队首元素，则直接删除之
		if (wait_q->tail == wait_q->head) {
			_nano_wait_q_reset(wait_q);
		} else {
			wait_q->head = tcs->link;
		}
	} else {
    	// 如果不是队首元素，先查找，再删除之
		struct tcs *prev = wait_q->head;

		while (prev->link != tcs) {
			prev = prev->link;
		}
		prev->link = tcs->link;
		if (wait_q->tail == tcs) {
			wait_q->tail = prev;
		}
	}

	tcs->nano_timeout.wait_q = NULL;
}
```
# _nano_timeout_abort
```
static inline int _nano_timeout_abort(struct tcs *tcs)
{
	return _do_nano_timeout_abort(&tcs->nano_timeout);
}
```
追踪 _do_nano_timeout_abort()：
```
int _do_nano_timeout_abort(struct _nano_timeout *t)
{
	sys_dlist_t *timeout_q = &_nanokernel.timeout_q;

	if (-1 == t->delta_ticks_from_prev) {
		return -1;
	}

	if (!sys_dlist_is_tail(timeout_q, &t->node)) {
		struct _nano_timeout *next =
			(struct _nano_timeout *)sys_dlist_peek_next(timeout_q,
								    &t->node);
        // 将该节点的超时时间补充给下一个节点，否则后续所有节点的超时时间都将产生错误
		next->delta_ticks_from_prev += t->delta_ticks_from_prev;
	}
	sys_dlist_remove(&t->node);
	t->delta_ticks_from_prev = -1;

	return 0;
}
```
函数很简单，将该 timeout 从超时链表中删除并做一些处理即可。

# _nano_get_earliest_timeouts_deadline
```
uint32_t _nano_get_earliest_timeouts_deadline(void)
{
	sys_dlist_t *q = &_nanokernel.timeout_q;
	struct _nano_timeout *t =
		(struct _nano_timeout *)sys_dlist_peek_head(q);

	return t ? min((uint32_t)t->delta_ticks_from_prev,
					(uint32_t)_nanokernel.task_timeout)
			 : (uint32_t)_nanokernel.task_timeout;
}
```
返回即将超时的节点。
> 这个 task_timeout 目前还没碰到过，今后再说






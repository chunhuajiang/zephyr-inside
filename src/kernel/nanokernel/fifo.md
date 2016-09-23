---
title: Zephys OS nano 内核篇：FIFO
date: 2016-09-20 14:33:21
categories: ["Zephyr OS"]
tags: [Zephyr]
---

- [FIFO 的概念](#fifo-的概念)
- [FIFO 的定义](#fifo-的定义)
- [FIFO 的初始化](#fifo-的初始化)
- [从 FIFO 中获取数据](#从-fifo-中获取数据)
    - [_fifo_get](#_fifo_get)
    - [nano_task_fifo_get](#nano_task_fifo_get)
- [向 FIFO 中添加数据](#向-fifo-中添加数据)
    - [_fifo_put_non_preemptible](#_fifo_put_non_preemptible)
    - [nano_task_fifo_put](#nano_task_fifo_put)

<!--more-->
# FIFO 的概念
nanokernel 中的 FIFO 对象是一种传统的先进先出队列的实现，它主要用于 fiber 上下文。

FIFO 是 Zephyr 内核用于在不同线程间传递数据的服务，向 FIFO 中添加数据和从 FIFO 中取出数据是一个异步的操作。

# FIFO 的定义
```
struct nano_fifo {
	struct _nano_queue wait_q;          /* waiting fibers */
	struct _nano_queue data_q;
#ifdef CONFIG_MICROKERNEL
	struct _nano_queue task_q;          /* waiting tasks */
#endif
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct nano_fifo *__next;
#endif
};
```
除去 micorkernel 的 task_q 和 用于表示的 __next，一共有两个变量，且它们的类型都是队列：
- wait_q:用于保存处于等待状态的fiber。当fiber试图向该fifo中取数据，但是该fifo中没有数据时，该fiber会被放入这个等待队列。
- data_q:用于保存fifo的数据。


# FIFO 的初始化
```
void nano_fifo_init(struct nano_fifo *fifo)
{
	_nano_wait_q_init(&fifo->wait_q);
	data_q_init(&fifo->data_q);

	_TASK_PENDQ_INIT(&fifo->task_q);

	SYS_TRACING_OBJ_INIT(nano_fifo, fifo);
}

static inline void data_q_init(struct _nano_queue *q)
{
	q->head = NULL;
	q->tail = &q->head;
}
```
初始化了fifo结构体中的各个成员。

# 从 FIFO 中获取数据
```
void *nano_fifo_get(struct nano_fifo *fifo, int32_t timeout)
{
	static void *(*func[3])(struct nano_fifo *, int32_t) = {
		nano_isr_fifo_get,
		nano_fiber_fifo_get,
		nano_task_fifo_get
	};

	return func[sys_execution_context_type_get()](fifo, timeout);
}
```

先看看函数的入参：
- fifo：待取数据的 fifo。
- timeout：取数据的超时等待时间，以滴答为单位。函数内部会根据该变量的值来做相应的处理。

再看看函数的返回值：
- NULL:获取数据失败。
- 非空：获取数据成功。

nano_fifo_get 会根据当前上下文的环境，调用对应的get函数。其中，nano_isr_fifo_get、nano_fiber_fifo_get是函数 _fifo_get 的别名。
## _fifo_get
```
void *_fifo_get(struct nano_fifo *fifo, int32_t timeout_in_ticks)
{
	unsigned int key;
	void *data = NULL;

	key = irq_lock();

	if (likely(!is_q_empty(&fifo->data_q))) {
    	// 如果数据队列data_q不为空，从该队列中取出数据。
		data = dequeue_data(fifo);
	} else if (timeout_in_ticks != TICKS_NONE) {
    	// 如果数据队列为空，将当前线程加入到等待队列wait_q，同时也将当前线程加入到超时链表中去，并绑定该超时
        // 节点的等待队列和超时时间。
		_NANO_TIMEOUT_ADD(&fifo->wait_q, timeout_in_ticks);
        // 并将当前线程加入到等待队列中。
		_nano_wait_q_put(&fifo->wait_q);
		data = (void *)_Swap(key);
		return data;
	}

	//　代码走到这里，说明获取数据失败，且立即返回
	irq_unlock(key);
	return data;
}
```
likely 是编译器内嵌的关键字，编译器会根据这个关键字对代码进行相应的优化，阅读代码时完全可以忽略。

当线程从 FIFO 中取数据时，有两种可能：
- FIFO 中有数据：即数据队列 data_q 不为空，此时就直接调用函数 dequeue_data() 取出数据队列中的队首数据，然后返回该数据的指针。
- FIFO 中没有数据：即数据队列 data_q 为空，无法取得数据，此时会根据入参 timeout_in_ticks 的值来做对应的处理：
  - 等于 TICKS_NONE，表示当取数据失败时，不等待，立即返回
  - 不等于 TICKS_NONE，表示获取该信号的线程将陷入阻塞状态。在它陷入阻塞后，有两种可能
    - 在 timeout_in_ticks 期间内，有另外一个线程向该 FIFO 中添加了一个数据，等待线程将被添加信号的线程唤醒，获取数据成功。
    - 在 timeout_in_ticks 期间内，没有线程向该 FIFO 中添加数据，那么等待将超时，定时器会将该线程唤醒，获取数据失败。

## nano_task_fifo_get
```
void *nano_task_fifo_get(struct nano_fifo *fifo, int32_t timeout_in_ticks)
{
	int64_t cur_ticks;
	int64_t limit = 0x7fffffffffffffffll;
	unsigned int key;

	key = irq_lock();
	cur_ticks = _NANO_TIMEOUT_TICK_GET();
	if (timeout_in_ticks != TICKS_UNLIMITED) {
		limit = cur_ticks + timeout_in_ticks;
	}

	do {
		/*
		 * Predict that the branch will be taken to break out of the
		 * loop.  There is little cost to a misprediction since that
		 * leads to idle.
		 */

		if (likely(!is_q_empty(&fifo->data_q))) {
			// fifo 中有数据，直接取出并返回
			void *data = dequeue_data(fifo);
			irq_unlock(key);
			return data;
		}

		if (timeout_in_ticks != TICKS_NONE) {
			_NANO_OBJECT_WAIT(&fifo->task_q, &fifo->data_q.head,
					timeout_in_ticks, key);
			cur_ticks = _NANO_TIMEOUT_TICK_GET();
			_NANO_TIMEOUT_UPDATE(timeout_in_ticks,
						limit, cur_ticks);
		}
	} while (cur_ticks < limit);

	irq_unlock(key);
	return NULL;
}
```
# 向 FIFO 中添加数据
```
void nano_fifo_put(struct nano_fifo *fifo, void *data)
{
	static void (*func[3])(struct nano_fifo *fifo, void *data) = {
		nano_isr_fifo_put,
		nano_fiber_fifo_put,
		nano_task_fifo_put
	};

	func[sys_execution_context_type_get()](fifo, data);
}
```
先看看入参：
- fifo：待放入数据的 fifo。
- data：待放入到该 fifo 中的数据。

nano_fifo_put 会根据当前上下文的环境，调用对应的put函数。其中，nano_isr_fifo_put、nano_fiber_fifo_put 都是函数 _fifo_put_non_preemptible 的别名。
## _fifo_put_non_preemptible
```
void _fifo_put_non_preemptible(struct nano_fifo *fifo, void *data)
{
	struct tcs *tcs;
	unsigned int key;

	key = irq_lock();

	// 从等待队列 wait_q 中取出队首元素
	tcs = _nano_wait_q_remove(&fifo->wait_q);
	if (tcs) {
    	// 等待队列中有线程正在等待
		_nano_timeout_abort(tcs);
		fiberRtnValueSet(tcs, (unsigned int)data);
	} else {
    	// 等待队列为空
		enqueue_data(fifo, data);
		_NANO_UNPEND_TASKS(&fifo->task_q);
	}

	irq_unlock(key);
}
```
当当前线程向 fifo 中放数据时，也有两种情况：
- 该 fifo 的等待队列为空：说明没有线程在等待获取数据，此时直接调用函数 enqueue_data 将数据放入 fifo 的数据队列 data_q 的队尾。
- 该 fifo 的等待队列非空：说明之前已有线程尝试获取数据，但是由于获取数据失败，正在等待 fifo 中的数据。此时我们不会将数据放入等待队列中，而是调用函数 fiberRtnValueSet() 直接将数据传递给等待队列中队首的线程。

> 目前还没弄明白 _Swip() 和 fiberRtnValueSet() 这两个函数具体的细节部分，这涉及到上下文切换的相关内容。

## nano_task_fifo_put

```
void nano_task_fifo_put(struct nano_fifo *fifo, void *data)
{
	struct tcs *tcs;
	unsigned int key;

	key = irq_lock();
	tcs = _nano_wait_q_remove(&fifo->wait_q);
	if (tcs) {
    	// 当前已有线程正在等待 fifo 中的数据，调用 _nano_timeout_abort() 函
        // 数将其从等待队列中移除，并加入到就绪链表中。
		_nano_timeout_abort(tcs);
        // 直接将数据传递给该线程
		fiberRtnValueSet(tcs, (unsigned int)data);
        // 切换上下文，让出 CPU 的使用权
		_Swap(key);
		return;
	}
	
    // 如果代码能走到这里，表明当前没有线程正在等待获取数据，那么直接将数据放入fifo的数据队列 data_q 中。
	enqueue_data(fifo, data);
	_TASK_NANO_UNPEND_TASKS(&fifo->task_q);

	irq_unlock(key);
}
```







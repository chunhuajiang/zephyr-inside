---
title: Zephys OS nano 内核篇：LIFO
date: 2016-09-23 15:23:30
categories: ["Zephyr OS"]
tags: [Zephyr]
---

LIFO 是与 FIFO 类似的一种服务，只是它是后进先出的而已。

- [LIFO 的类型定义](#lifo-的类型定义)
- [LIFO 的初始化](#lifo-的初始化)
- [从 LIFO 中获取数据](#从-lifo-中获取数据)
    - [_lifo_get](#_lifo_get)
    - [nano_task_lifo_get](#nano_task_lifo_get)
- [向 LIFO 中添加数据](#向-lifo-中添加数据)
    - [_lifo_put_non_preemptible](#_lifo_put_non_preemptible)
    - [nano_task_lifo_put](#nano_task_lifo_put)

<!--more-->
# LIFO 的类型定义
```
struct nano_lifo {
	struct _nano_queue wait_q;
	void *list;
#ifdef CONFIG_MICROKERNEL
	struct _nano_queue task_q;          /* waiting tasks */
#endif
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct nano_lifo *__next;
#endif
};
```
除去 micorkernel 的 task_q 和 用于表示的 __next，一共有两个变量，且它们的类型都是队列：
- wait_q:用于保存处于等待状态的fiber。当fiber试图向该lifo中取数据，但是该lifo中没有数据时，该fiber会被放入这个等待队列。
- list:用于指向lifo的数据。

# LIFO 的初始化
```
void nano_lifo_init(struct nano_lifo *lifo)
{
	lifo->list = (void *) 0;
	_nano_wait_q_init(&lifo->wait_q);
	SYS_TRACING_OBJ_INIT(nano_lifo, lifo);
	_TASK_PENDQ_INIT(&lifo->task_q);
}
```
初始化了lifo结构体中的各个成员。

# 从 LIFO 中获取数据
```
void *nano_lifo_get(struct nano_lifo *lifo, int32_t timeout)
{
	static void *(*func[3])(struct nano_lifo *, int32_t) = {
		nano_isr_lifo_get,
		nano_fiber_lifo_get,
		nano_task_lifo_get
	};

	return func[sys_execution_context_type_get()](lifo, timeout);
}
```
先看看函数的入参：
- lifo：待取数据的 fifo。
- timeout：取数据的超时等待时间，以滴答为单位。函数内部会根据该变量的值来做相应的处理。

再看看函数的返回值：
- NULL:获取数据失败。
- 非空：获取数据成功。

nano_lifo_get 会根据当前上下文的环境，调用对应的get函数。其中，nano_isr_lifo_get、nano_fiber_lifo_get 是函数 _lifo_get 的别名。
## _lifo_get
```
void *_lifo_get(struct nano_lifo *lifo, int32_t timeout_in_ticks)
{
	void *data = NULL;
	unsigned int imask;

	imask = irq_lock();

	if (likely(lifo->list != NULL)) {
    	// 如果数据链表指针 list 不为空，从该链表表头取出数据。
        
    	// 将data指向链表的表头，并将链表指针后移
    	// 没看懂，看来C基础还不够，需要补习补习啊
		data = lifo->list;
		lifo->list = *(void **) data;
	} else if (timeout_in_ticks != TICKS_NONE) {
		// 如果数据链表为空，且超时等待时间不为 TICKS_NONE，
		// 将当前线程加入到内核的超时链表中
		_NANO_TIMEOUT_ADD(&lifo->wait_q, timeout_in_ticks);
		// 再将丢弃线程加入到该lifo的等待队里中
		_nano_wait_q_put(&lifo->wait_q);
		// 切换上下文，然后当前线程会陷入阻塞状态
		data = (void *) _Swap(imask);
		return data;
	}
	
	// 如果代码走到这里，说明获取数据失败
	irq_unlock(imask);
	return data;
}
```
likely 是编译器内嵌的关键字，编译器会根据这个关键字对代码进行相应的优化，阅读代码时完全可以忽略。

当线程从 LIFO 中取数据时，有两种可能：
- LIFO 中有数据：即数据链表指针 list 不空，此时就直接调用函数 dequeue_data() 取出数据队列中的队首数据，然后返回该数据的指针。
- LIFO 中没有数据：即数据链表指针 list 为空，无法取得数据，此时会根据入参 timeout_in_ticks 的值来做对应的处理：
  - 等于 TICKS_NONE，表示当取数据失败时，不等待，立即返回
  - 不等于 TICKS_NONE，表示获取该信号的线程将陷入阻塞状态。在它陷入阻塞后，有两种可能
    - 在 timeout_in_ticks 期间内，有另外一个线程向该 LIFO 中添加了一个数据，等待线程将被添加信号的线程唤醒，获取数据成功。
    - 在 timeout_in_ticks 期间内，没有线程向该 LIFO 中添加数据，那么等待将超时，定时器会将该线程唤醒，获取数据失败。

## nano_task_lifo_get

```
void *nano_task_lifo_get(struct nano_lifo *lifo, int32_t timeout_in_ticks)
{
	int64_t cur_ticks;
	int64_t limit = 0x7fffffffffffffffll;
	unsigned int imask;

	imask = irq_lock();
	// 获取当前的系统滴答数
	cur_ticks = _NANO_TIMEOUT_TICK_GET();
	if (timeout_in_ticks != TICKS_UNLIMITED) {
		// 计算等待时间到期后的滴答数
		limit = cur_ticks + timeout_in_ticks;
	}

	do {
		if (likely(lifo->list != NULL)) {
			// 如果数据链表中有数据，则取出数据
			void *data = lifo->list;
			lifo->list = *(void **) data;
			irq_unlock(imask);
			return data;
		}

		if (timeout_in_ticks != TICKS_NONE) {
			// 让 cpu 加入低功耗模式，陷入睡眠状态。当有外部中断到来
			// 时(比如systick中断)，cpu 被唤醒，继续执行，具体分析请
			// 见《Zephyr OS nano 内核篇：信号量》一文
			_NANO_OBJECT_WAIT(&lifo->task_q, &lifo->list,
					timeout_in_ticks, imask);
			// 获取并更新当前的滴答数，用作循环的判断条件，判断是否跳出循环
			cur_ticks = _NANO_TIMEOUT_TICK_GET();
			_NANO_TIMEOUT_UPDATE(timeout_in_ticks,
						limit, cur_ticks);
		}
		// 如果　timeout_in_ticks 等于 TICKS_NONE，那么 cur_ticks 等于 limit
        // 循环判断的条件将失败，跳出循环，本函数立即返回，获取数据失败
	} while (cur_ticks < limit);

	irq_unlock(imask);

	return NULL;
}
```



# 向 LIFO 中添加数据

```
void nano_lifo_put(struct nano_lifo *lifo, void *data)
{
	static void (*func[3])(struct nano_lifo *, void *) = {
		nano_isr_lifo_put,
		nano_fiber_lifo_put,
		nano_task_lifo_put
	};

	func[sys_execution_context_type_get()](lifo, data);
}
```



根据当前上下文的类型，调用对应的添加数据的函数。其中，nano_isr_lifo_put() 和 nano_fiber_lifo_put() 是函数 _lifo_put_non_preemptible()的别名。

## _lifo_put_non_preemptible

```
void _lifo_put_non_preemptible(struct nano_lifo *lifo, void *data)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();
	// 取出lifo的等待队列中的队首数据，判断有没有现成在等待信号
	tcs = _nano_wait_q_remove(&lifo->wait_q);
	if (tcs) {
		// 如果有线程在等待信号，将该线程从超时队列中删除
		// 同时 _nano_wait_q_remove 还会将该线程从阻塞态转为就绪态
		_nano_timeout_abort(tcs);
		// 此时不直接向lifo中添加数据，直接将数据传递给正在获取数据的线程
		fiberRtnValueSet(tcs, (unsigned int) data);
	} else {
		// 如果没有线程在等待数据，直接将数据放入lifo的数据链表的表头
		*(void **) data = lifo->list;
		lifo->list = data;
		_NANO_UNPEND_TASKS(&lifo->task_q);
	}

	irq_unlock(imask);
}
```

前面在从lifo中获取数据时，如果获取数据失败，做了两件事儿：

- 将线程阻塞(加入lifo的等待队列中)
- 将线程加入到内核大总管 _nanokernel 维护的超时链表中

对应的，在往lifo中添加数据时，如果判断出有线程处于等待状态，也做了两件事儿：

- 将阻塞线程添加到就绪链表中
- 将阻塞线程从超时链表中删除

## nano_task_lifo_put

```
void nano_task_lifo_put(struct nano_lifo *lifo, void *data)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();
	// 取出lifo的等待队列的队首数据，判断有没有线程在等待信号
	tcs = _nano_wait_q_remove(&lifo->wait_q);
	if (tcs) {
		// 如果有线程在等待数据，将该线程从超时队列中删除
		// 此外，_nano_wait_q_remove 内部会将队首的线程加入到就绪队列
		_nano_timeout_abort(tcs);
		// 直接将数据的地址返回给等待线程
		fiberRtnValueSet(tcs, (unsigned int) data);
		由于 wait_q 中保持的是 fiber，而当前的线程是 task，所以让出 cpu，让该 fiber 先运行。
		_Swap(imask);
		return;
	}

	// 代码走到这里，说明之前没有线程在等待数据
	// 直接将数据放到lifo的数据链表中
	*(void **) data = lifo->list;
	lifo->list = data;
	_TASK_NANO_UNPEND_TASKS(&lifo->task_q);

	irq_unlock(imask);
}
```





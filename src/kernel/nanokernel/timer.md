---
title: Zephys OS nano内核篇：定时器 Timer
date: 2016-09-19 12:56:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---

- [概念](#概念)
- [Timer 的定义](#timer-的定义)
- [Timer 的 API](#timer-的-api)
    - [nano_timer_init](#nano_timer_init)
    - [nano_timer_start](#nano_timer_start)
    - [nano_timer_test](#nano_timer_test)
        - [nano_fiber_timer_test](#nano_fiber_timer_test)
        - [nano_task_timer_test](#nano_task_timer_test)
        - [nano_isr_timer_test](#nano_isr_timer_test)
    - [nano_timer_stop](#nano_timer_stop)
        - [nano_fiber_timer_stop](#nano_fiber_timer_stop)
        - [nano_isr_timer_stop](#nano_isr_timer_stop)
        - [nano_task_timer_stop](#nano_task_timer_stop)
    - [nano_timer_ticks_remain](#nano_timer_ticks_remain)

<!--more-->

# 概念
nanokernel 利用系统的时钟实现了一个定时器服务。线程可以利用定时器服务来等待一段指定的时间间隔(以滴答为单位)，且在等待的期间可以异步执行其它工作。一个线程可以使用多个定时器同时监控多个时间间隔。

线程在使用定时器时，可以为定时器绑定一个用户数据(使用一个指向用户数据结构体的指针)。当定时器的时间到期时，它会返回这个用户数据。

# Timer 的定义
```
struct nano_timer {
	struct _nano_timeout timeout_data;
	void *user_data;
	void *user_data_backup;
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct nano_timer *__next;
#endif
};
```
不考虑用于 debug 的 __next,一共包含 3 个成员：
- timeout_data: 可以看出来，定时器内部使用了前一篇文章所讲的超时服务。
- user_data: 用户数据，定时器到期后返回给线程。
- user_data_backup: 用户数据的备份。

> 为什么需要备份用户数据？表面上看去，这个备份完全是多余的，但是深入分析，其实定时器同时还使用 user_data 来作为一个标志，来表示定时器当前的状态。当定时器处于工作状态(即定时器已启动，并在等待到期)时，user_data 指向一段用户自定义数据。当定时器处于非工作状态(即定时器启动前、定时器到期后或者定时器被终止后)时，user_data 指向 NULL。
> 
> Q：为什么不单独使用一个 flag 成员来表示当前的状态，那样更容易理解

# Timer 的 API

Timer 服务对内核其它服务暴露了如下 API 如下：
- **nano_timer_init**()：初始化定时器
- **nano_timer_start**()：启动定时器。内核会根据当前的上下文调用对于的启动函数：
	- nano_task_timer_start()
	- nano_fiber_timer_start()
	- nano_isr_timer_start()
- **nano_timer_test**()：测试定时器是否到期。内核会根据当前的上下文调用对应的测试函数：
	- nano_task_timer_test()
	- nano_fiber_timer_test()
	- nano_isr_timer_test()
- **nano_timer_stop**()：强行停止定时器，将其从超时链表中删除，并将绑定的线程加入就绪队列，因此也可以将其理解为将定时器强制到期。内核会根据当前的上下文调用对于的停止函数：
	- nano_task_timer_stop()
	- nano_fiber_timer_stop()
	- nano_isr_timer_stop()
- **nano_timer_ticks_remain**()：判断定时器还有多久将到期，单位是滴答。

## nano_timer_init
```
void nano_timer_init(struct nano_timer *timer, void *data)
{
	// 初始化 timeout_data
	_nano_timeout_init(&timer->timeout_data, NULL);
	timer->user_data = NULL;
	timer->user_data_backup = data;

	SYS_TRACING_OBJ_INIT(nano_timer, timer); // 用于debug
}
```
在启动刚定时器前，需要调用该函数初始化定时器结构体中的各成员。需要注意到一点，user_data 没有指向用户数据，user_data_backup 指向了用户数据，具体的原因，请参考后面 nano_timer_test() 的分析。

## nano_timer_start
nano_timer_start(),nano_task_timer_start(),nano_fiber_timer_start(),nano_isr_timer_start()都是函数_timer_start() 的别名：
```
FUNC_ALIAS(_timer_start, nano_isr_timer_start, void);
FUNC_ALIAS(_timer_start, nano_fiber_timer_start, void);
FUNC_ALIAS(_timer_start, nano_task_timer_start, void);
FUNC_ALIAS(_timer_start, nano_timer_start, void);
```
```
void _timer_start(struct nano_timer *timer, int ticks)
{
	int key = irq_lock();

	timer->user_data = timer->user_data_backup;
	_nano_timer_timeout_add(&timer->timeout_data,
				NULL, ticks);
	irq_unlock(key);
}
```
启动定时器，并设定定时器到期的时间间隔(以滴答为单位)。主要做了两件事：
- 将user_data 也指向用户数据。
- 将定时器结构体中的超时服务加入到内核的超时链表中。

## nano_timer_test
```
void *nano_timer_test(struct nano_timer *timer, int32_t timeout_in_ticks)
{
	static void *(*func[3])(struct nano_timer *, int32_t) = {
		nano_isr_timer_test,
		nano_fiber_timer_test,
		nano_task_timer_test,
	};

	return func[sys_execution_context_type_get()](timer, timeout_in_ticks);
}
```
根据当前的上下文，调用对应的测试函数。第二个比较难以理解，它其实是一个标志 flag，用来指示该函数的具体行为：
- 如果 flag 的取值为 TICKS_NONE，表示如果待测试的定时器如果没到期，该函数直接返回。
- 如果 flag 的取值为 TICKS_UNLIMITED，表示如果待测试的定时器如果没到期，会让出 CPU 进行上下文切换或忙进行忙等待(如果当前上下文是中断，不会切换)。

### nano_fiber_timer_test
```
void *nano_fiber_timer_test(struct nano_timer *timer, int32_t timeout_in_ticks)
{
	int key = irq_lock();
	struct _nano_timeout *t = &timer->timeout_data;
	void *user_data;
    
	// 根据 _nano_timer_expire_wait 的返回值判读是直接返回还是进行线程切换。
	if (_nano_timer_expire_wait(timer, timeout_in_ticks, &user_data)) {
		t->tcs = _nanokernel.current;
		_Swap(key);
		key = irq_lock();
		user_data = timer->user_data;
		timer->user_data = NULL;
	}
	irq_unlock(key);
	return user_data;
}
```
再看看 _nano_timer_expire_wait() 如何实现：
```
tatic int _nano_timer_expire_wait(struct nano_timer *timer,
				    int32_t timeout_in_ticks,
				    void **user_data_ptr)
{
	struct _nano_timeout *t = &timer->timeout_data;

	/* check if the timer has expired */
	if (t->delta_ticks_from_prev == -1) {
    	// 将定时器的用户数据“取”给 user_data_ptr
		*user_data_ptr = timer->user_data;
        // 用户数据被“取”走后，将 user_data 置为 NULL
		timer->user_data = NULL;
	/* if the thread should not wait, return immediately */
	} else if (timeout_in_ticks == TICKS_NONE) {
    	// 由于定时器没到期，调用函数“取”不到任何数据
		*user_data_ptr = NULL;
	} else {
    	// 由于调用函数将进行上下文切换，此时不关心 user_data_ptr
		return 1;
	}
	return 0;
}
```
该函数先检查定时器是否已经到期了。
- 如果到期了，返回 0 ，“取”出用户数据，其调用函数不会进行线程切换。
- 如果没到期，再根据传入的标志 timeout_in_ticks 来判断具体的行为。
  - 如果 timeout_in_ticks 为 TICKS_NONE，返回 0，其调用函数不会进行上下文切换。
  - 如果 timeout_in_ticks 为 TICKS_UNLIMITED，返回 1，其调用函数将上下文切换。

我们现在可以回头看看为什么用户数据需要备份了。在初始化时，
### nano_task_timer_test
```
void *nano_task_timer_test(struct nano_timer *timer, int32_t timeout_in_ticks)
{
	int key = irq_lock();
	struct _nano_timeout *t = &timer->timeout_data;
	void *user_data;

	if (_nano_timer_expire_wait(timer, timeout_in_ticks, &user_data)) {
		// 进行忙等待操作，知道定时器到期。
		while (t->delta_ticks_from_prev != -1) {
			NANO_TASK_TIMER_PEND(timer, key);
		}
		user_data = timer->user_data;
		timer->user_data = NULL;
	}
	irq_unlock(key);
	return user_data;
}
```
NANO_TASK_TIMER_PEND 会判断当前 task 是否是 idea task 来做相应的动作，如果是 idea task，直接进行忙等待。如果不是 idea task，将当前 task 挂起到一个定时器上。
### nano_isr_timer_test
```
void *nano_isr_timer_test(struct nano_timer *timer, int32_t timeout_in_ticks)
{
	int key = irq_lock();
	void *user_data;

	if (_nano_timer_expire_wait(timer, timeout_in_ticks, &user_data)) {
		// 由于中断上下文的需要需要快速处于终端，所以即使 _nano_timer_expire_wait 返回 1，
        // 本函数也直接返回
		user_data = NULL;
	}
	irq_unlock(key);
	return user_data;
}
```
## nano_timer_stop
```
void nano_timer_stop(struct nano_timer *timer)
{
	static void (*func[3])(struct nano_timer *) = {
		nano_isr_timer_stop,
		nano_fiber_timer_stop,
		nano_task_timer_stop,
	};

	func[sys_execution_context_type_get()](timer);
}
```
根据当前上下文，调用对应的定时器停止函数。
### nano_fiber_timer_stop
### nano_isr_timer_stop
nano_fiber_timer_stop()和nano_isr_timer_stop()都是函数 _timer_stop_non_preemptible() 的别名：
```
FUNC_ALIAS(_timer_stop_non_preemptible, nano_isr_timer_stop, void);
FUNC_ALIAS(_timer_stop_non_preemptible, nano_fiber_timer_stop, void);
```
所以我们具体来看 _timer_stop_non_preemptible() 函数：
```
void _timer_stop_non_preemptible(struct nano_timer *timer)
{
	struct _nano_timeout *t = &timer->timeout_data;
	struct tcs *tcs = t->tcs;
	int key = irq_lock();

	// 1. 先判断定时器所绑定的线程是否处于一个等待队列上。如果是，让其继续等待，当等待条
    // 件被满足时会有相应的程序将其加入到就绪队列中，我们不用做任何处理。
    // 2. 如果不在等待队列上，将 timeout_data 从超时链表中删除。
    // 3. 再根据定时器绑定的线程的上下文类型，将其加入到对应的就绪链表中。
	if (!t->wait_q && (_nano_timer_timeout_abort(t) == 0) &&
	    tcs != NULL) {
		if (_IS_MICROKERNEL_TASK(tcs)) {
			_NANO_TIMER_TASK_READY(tcs);
		} else {
			_nano_fiber_ready(tcs);
		}
	}

	// 标志定时器处于非工作状态
	timer->user_data = NULL;
	irq_unlock(key);
}
```
### nano_task_timer_stop
```
void nano_task_timer_stop(struct nano_timer *timer)
{
	struct _nano_timeout *t = &timer->timeout_data;
	struct tcs *tcs = t->tcs;
	int key = irq_lock();

	timer->user_data = NULL;

	if (!t->wait_q && (_nano_timer_timeout_abort(t) == 0) &&
	    tcs != NULL) {
		if (!_IS_MICROKERNEL_TASK(tcs)) {
			_nano_fiber_ready(tcs);
			_Swap(key);
			return;
		}
		_TASK_NANO_TIMER_TASK_READY(tcs);
	}
	irq_unlock(key);
}
```
该函数与 _timer_stop_non_preemptible 极其相似，主要的区别是：

由于调用该函数时，当前上下文是 task，所以如果判断出定时器所绑定的线程的上下文是 fiber 或者 isr 时，就进行上下文切换。这是因为 task 的优先级比 fiber 和 isr 的优先级低。

## nano_timer_ticks_remain
```
int32_t nano_timer_ticks_remain(struct nano_timer *timer)
{
	int key = irq_lock();
	int32_t remaining_ticks;
	struct _nano_timeout *t = &timer->timeout_data;
	sys_dlist_t *timeout_q = &_nanokernel.timeout_q;
	struct _nano_timeout *iterator;

	if (t->delta_ticks_from_prev == -1) {
    	// 如果定时器已到期，直接返回 0
		remaining_ticks = 0;
	} else {
		// 如果定时器没到期，从链表头开始查找，直到找到该节点，并将各节点绑定的增量超
        // 时时间 delta_ticks_from_prev 累加
		iterator = (struct _nano_timeout *)sys_dlist_peek_head(timeout_q);
		remaining_ticks = iterator->delta_ticks_from_prev;
		while (iterator != t) {
			iterator = (struct _nano_timeout *)sys_dlist_peek_next(timeout_q, &iterator->node);
			remaining_ticks += iterator->delta_ticks_from_prev;
		}
	}

	irq_unlock(key);
	return remaining_ticks;
}
```







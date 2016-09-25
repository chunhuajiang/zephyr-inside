---
title: Zephys OS nano 内核篇：信号量 semaphore
date: 2016-09-23 12:53:59
categories: ["Zephyr OS"]
tags: [Zephyr]
---

信号量是 Zephyr OS 提供的用于不同线程间同步的机制。目前，Zephyr OS 只提供了信号量这一种同步机制。

- [信号量的类型定义](#信号量的类型定义)
- [信号量的初始化](#信号量的初始化)
- [获取信号](#获取信号)
    - [_sem_take](#_sem_take)
    - [nano_task_sem_take](#nano_task_sem_take)
- [释放(发送)信号](#释放发送信号)
    - [_sem_give_non_preemptible](#_sem_give_non_preemptible)
    - [nano_task_sem_give](#nano_task_sem_give)

<!--more-->

# 信号量的类型定义
```
struct nano_sem {
	struct _nano_queue wait_q;
	int nsig;
#ifdef CONFIG_MICROKERNEL
	struct _nano_queue task_q;          /* waiting tasks */
#endif
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct nano_sem *__next;
#endif
};
```
不考虑 microkernel 的 task_q 和用于调试的 __next，信号量包含两个成员：
- nsig：信号量的值，即信号量的信号。当该值为 0，表示没有有效信号；当该值大于 0，表示有信号可以获取。
- wait_q：该信号量维护的等待队列。当一个线程试图获取无效的信号量(即信号量的值 nsig 为零)时，它可能会加入到这个等待队列中，然后陷入阻塞状态。

# 信号量的初始化
```
void nano_sem_init(struct nano_sem *sem)
{
	sem->nsig = 0;
	_nano_wait_q_init(&sem->wait_q);
	SYS_TRACING_OBJ_INIT(nano_sem, sem); // 用于调试
	_TASK_PENDQ_INIT(&sem->task_q);		 // microkernel 才使用的
}
```
初始化信号量结构体中各成员：
- 将信号量的值初始化为 0。
- 初始化信号量的等待队列。


# 获取信号
```
int nano_sem_take(struct nano_sem *sem, int32_t timeout)
{
	static int (*func[3])(struct nano_sem *, int32_t) = {
		nano_isr_sem_take,
		nano_fiber_sem_take,
		nano_task_sem_take
	};

	return func[sys_execution_context_type_get()](sem, timeout);
}
```
先看看函数的入参：
- sem：希望获取信号的信号量。
- timeout：获取信号的超时等待时间，以滴答为单位。函数内部会根据该变量的值来做相应的处理。

再看看函数的返回值：
- 1 - 表示获取信号成功
- 0 - 表示获取信号失败

nano_sem_take 会根据当前上下文的类型，调用对应的获取信号的函数。其中，nano_isr_sem_take() 和 nano_fiber_sem_take() 是函数 _sem_take() 的别名。

## _sem_take
```
int _sem_take(struct nano_sem *sem, int32_t timeout_in_ticks)
{
	unsigned int key = irq_lock();

	if (likely(sem->nsig > 0)) {
    	// nsig > 0,说明可以获取信号
        // 然后将信号量的值 nsig 递减
        // 然后返回 1,表示获取信号成功
		sem->nsig--;
		irq_unlock(key);
		return 1;
	}
	
    // 代码走到这里，说明当前没有有效的信号
	if (timeout_in_ticks != TICKS_NONE) {
    	// 将当前线程加入内核的超时链表中，并绑定该超时节点的等待队列为
        // 当前信号量所维护的等待队列
		_NANO_TIMEOUT_ADD(&sem->wait_q, timeout_in_ticks);
        // 将当前线程加入到该信号量维护的等待队列
		_nano_wait_q_put(&sem->wait_q);
		// return _Swap(key);
		/* 原文是 return _Swap(key)，但是为了分析说明，我们将其拆分为下面两句话 */
		int value = _Swap(key);
		// 执行完 _Swap() 函数后，将会切换到其它上下文。如果该函数返回了，有两种可能：
		// 1. 有线程向该信号量中添加了限号，唤醒了本线程，且在唤醒前设置了本线程的返回值，
		//    具体信息可参考函数 _sem_give_non_preemptible
		// 2. 由于等待超时，超时服务唤醒了本线程，本线程的返回值没有被设置，返回默认值 0
        reutrn value;
	}

	//　代码走到这里，说明获取信号失败，且立即返回
	irq_unlock(key);
	return 0;
}
```
likely 是编译器内嵌的关键字，编译器会根据这个关键字对代码进行相应的优化，阅读代码时完全可以忽略。

当线程尝试从信号量中获取信号时，有两种可能：
- 信号量中有有效信号：即 nsig 的值大于 0，将 nsig 递减，获取信号成功。
- 信号量中没有有效信号：即 nsig 的值等于 0，无法获取信号，此时会根据入参 timeout_in_ticks 的值来做对应的处理：
  - 等于 TICKS_NONE，表示当信号失败时，不等待，立即返回
  - 不等于 TICKS_NONE，表示获取该信号的线程将陷入阻塞状态。在它陷入阻塞后，有两种可能
    - 在 timeout_in_ticks 期间内，有另外一个线程向该信号量中添加了一个信号，等待线程将被添加信号的线程唤醒，获取信号成功。
    - 在 timeout_in_ticks 期间内，没有线程向该信号量中添加值，那么等待将超时，定时器会将该线程唤醒，获取信号失败。

## nano_task_sem_take
```
int nano_task_sem_take(struct nano_sem *sem, int32_t timeout_in_ticks)
{
	int64_t cur_ticks;
	int64_t limit = 0x7fffffffffffffffll; // 为什么这样初始化，不解
	unsigned int key;

	key = irq_lock();
    // 获取当前的系统滴答数
	cur_ticks = _NANO_TIMEOUT_TICK_GET();
	if (timeout_in_ticks != TICKS_UNLIMITED) {
    	// 计算等待时间到期后的滴答数
		limit = cur_ticks + timeout_in_ticks;
	}

	do {
		if (likely(sem->nsig > 0)) {
            // nsig > 0,说明可以获取信号
        	// 然后将信号量的值 nsig 递减
       	 	// 然后返回 1,表示获取信号成功
			sem->nsig--;
			irq_unlock(key);
			return 1;
		}

		if (timeout_in_ticks != TICKS_NONE) {
			// 让 task 等待，具体请见后面的分析
			_NANO_OBJECT_WAIT(&sem->task_q, &sem->nsig,
					timeout_in_ticks, key);

             // 获取并更新当前的滴答数，用作循环的判断条件，判断是否跳出循环
			cur_ticks = _NANO_TIMEOUT_TICK_GET();
			_NANO_TIMEOUT_UPDATE(timeout_in_ticks,
						limit, cur_ticks);
		}
        // 如果　timeout_in_ticks 等于 TICKS_NONE，那么 cur_ticks 等于 limit
        // 循环判断的条件将失败，跳出循环，本函数立即返回，获取信号失败
	} while (cur_ticks < limit);

	irq_unlock(key);
	return 0;
}
```
_NANO_OBJECT_WAIT() 是一个宏，对于 nanokernel，它的原型如下：
```
#define _NANO_OBJECT_WAIT(queue, data, timeout, key)     \
		do {                                             \
			_NANO_TIMEOUT_SET_TASK_TIMEOUT(timeout); \
			nano_cpu_atomic_idle(key);               \
			key = irq_lock();                        \
		} while (0)
```
_NANO_TIMEOUT_SET_TASK_TIMEOUT()是设置内核大总管 _nanokernel 中 task_timeout 的值,目前还没发现这个有什么用。
nano_cpu_atomic_idle() 是用汇编实现的一个函数，它将使 CPU 进入睡眠状态，并在接收到中断后被唤醒。其原型如下：
```
SECTION_FUNC(TEXT, nano_cpu_atomic_idle)
	// 本函数使用了两个通用寄存器,r0 和 r1。
    // r0：调用者传递进来的中断的 mask
    // r1：用于设置 BASEPRI 的值

	//　异或操作，将 r1 与 r1，进行异或操作，将结果保存到 r1 中，所以 r1 里面的值为 0
    // .n 用于告诉编译器使用 16 位的指令进行汇编
    eors.n r1, r1

    // 锁定 PRIMASK, 此时系统不会处理中断
    cpsid i

    // 将 0 写入寄存器 BASEPRI，此时系统将能够接收**所有**中断
    msr BASEPRI, r1

	// 此时的状态：能接收中断，但是先不处理中断
    
    // wfe，Wait For Event，等待事件的到来。执行这个指令后，CPU 将进入睡眠状态，进入低功
    // 耗模式。更具体地说，执行 wfe　指令后，CPU core 将会发送一个信号，pmu 收到这个信号后，
    // 将关闭 core 的 clock，甚至进入 retention 模式(降低电压，但是保存寄存器和cache 的值)。
    wfe
	
    // 此时 cpu 陷入睡眠了，不再取指执行。
    
	// 当有外部中断到来时，将会唤醒 CPU,然后继续执行下面的指令.
    
    // 恢复睡眠之前的中断优先级
    msr BASEPRI, r0
    
    // 允许执行之前检测到的中断信号的 ISR
    cpsie i
    
    // 可能会在这里执行 ISR.
    
    // 返回调用函数
    bx lr
```

# 释放(发送)信号
```
void nano_sem_give(struct nano_sem *sem)
{
	static void (*func[3])(struct nano_sem *sem) = {
		nano_isr_sem_give,
		nano_fiber_sem_give,
		nano_task_sem_give
	};

	func[sys_execution_context_type_get()](sem);
}
```
根据当前上下文的类型，调用对应的添加信号量的函数。其中，nano_isr_sem_give() 和 nano_fiber_sem_give() 是函数 _sem_give_non_preemptible()的别名。

我之所以将这个函数叫做释放信号或发送信号，是因为信号量的两种应用场景：
- 当一个线程对某个临界资源访问前，它先要获取信号，访问完后，还需要释放信号
- 当一个线程获取信号时，被陷入阻塞状态。此时如果有另一个线程释放了信号，阻塞的线程将被唤醒。我们可以将其利皆为该线程对阻塞的线程发送了一个唤醒信号。

## _sem_give_non_preemptible
```
void _sem_give_non_preemptible(struct nano_sem *sem)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();
    // 取出信号量的等待队列的队首数据，判断有没有线程在等待信号
	tcs = _nano_wait_q_remove(&sem->wait_q);
	if (!tcs) {
    	// 如果没有线程在等待信号，直接将信号量的值递增
        // 此外，_nano_wait_q_remove 内部会将队首的线程加入到就绪队列
        // 即该线程的状态由阻塞态变为了就绪态
		sem->nsig++;
		_NANO_UNPEND_TASKS(&sem->task_q);
	} else {
    	//　如果有线程在等待信号，将该线程从超时队列中删除
		_nano_timeout_abort(tcs);
        // 此时不设置信号量的值，直接设置等待线程的返回值为 1
		set_sem_available(tcs);
	}

	irq_unlock(imask);
}
```
前面在从信号量中获取信号时，如果线程获取信号失败，做了两件事儿：
- 将线程阻塞(加入等待队列中)
- 将线程加入超时链表中

对应的，在往信号量中添加信号时，如果判断出有线程处于等待状态，也做了两件事儿：
- 将阻塞的线程添加到就绪链表中
- 将线程从超时链表中删除

## nano_task_sem_give
```
void nano_task_sem_give(struct nano_sem *sem)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();
    // 取出信号量的等待队列的队首数据，判断有没有线程在等待信号
	tcs = _nano_wait_q_remove(&sem->wait_q);
	if (tcs) {
    	// 如果有线程在等待信号，将该线程从超时队列中删除
        // 此外，_nano_wait_q_remove 内部会将队首的线程加入到就绪队列
		_nano_timeout_abort(tcs);
        // 此时不设置信号量的值，直接设置等待线程的返回值为 1
		set_sem_available(tcs);
        由于 wait_q 中保存的线程是 fiber，而当前的线程是 task，所以让出 cpu，让该 fiber 先运行。
		_Swap(imask);
		return;
	}
	
    // 代码走到这里，说明之前没有线程在等待信号
    // 将信号量的值递增
	sem->nsig++;
	_TASK_NANO_UNPEND_TASKS(&sem->task_q);

	irq_unlock(imask);
}
```

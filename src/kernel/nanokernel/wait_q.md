---
title: Zephyr OS nano 内核篇： 等待队列 wait_q
date: 2016-09-08 21:21:05
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本文先描述 Zephyr OS 中线程的状态关系，然后分析线程的等待队列的相关操作。
<!--more-->
Zephyr OS 中的等待队列相关的代码很少，仅有几十行，但是理解这些代码却不是那么轻松，因此为了便于大家理解，画了若干图。

# 线程的状态切换
Zephyr OS 中线程的状态可以分为三类：
- 执行态：指当前正在占用 CPU 执行任务的线程。由于物联网设备的低成本、低速率的特性，Zephyr OS 只支持单 CPU，因此内核中只有一个线程处于执行态。
- 就绪态：指已经准备就绪、等待被调度执行的线程，这些线程以优先级的顺序排列。当系统当前正在执行的线程执行完毕或进入等待队列时，调度算法会调度就绪态链表中优先级最高的线程。
- 等待态：当内核中的一个线程正在执行时，可能由于某种原因无法再执行下去(比如等待某种资源——信号量)，这时我们可以将该线程放入一个等待队列中，然后将 CPU 的执行权转交给其它线程，以达到最大效率使用 CPU 的目的。

线程的状态切换如图 1 所示。
<center>![](/images/zephyr/kernel/nanokernel/wait_q/1.png)</center>
<center>图 1. 线程状态切换</center>

# 等待队列的应用场景

Zephyr OS 中，以下几种场景将会使用等待队列：

- 信号量：当多个线程都需要使用信号量时，可能信号量被别的线程用尽(信号量减至0)，另一个线程再去获取该信号量时，得不到信号量，该线程就将自己加入到等待队列中，并释放 CPU。
- fifo：fifo 是先进先出的队列，使用的场景是这样的：某个线程(生产者)向 fifo 中写数据，另一个线程(消费者)从 fifo 中读取数据。当读线程(消费者)从 fifo 中取数据时是空的，该线程就将自己加入到等待队列中，并释放 CPU。
- lifo：lifo 是后进先出的队列，使用的场景与 fifo 类似。
- timeout：超时服务是指线程在指定的超时时间后再运行。线程在使用超时服务时，会将自己加入到等待队列中。当超时时间到期时，调度器会将该线程从等待队列中取出。

> 以上内容都是推测出来的，其正确与否会在今后的学习过程中得到验证。


# 等待队列的定义
```
struct _nano_queue {
	void *head;
	void *tail;
};
```

该结构体包含两个成员：
- head：用于指向等待队列的队首线程。当队列为空时，指向NULL。
- tail：用于指向等待队列的队尾线程。当队列位空时，指向该队列本身。

对于如下程序：
```
struct _nano_queue wait_q;
```

其在内存空间存储情况如图 2 所示。
<center>![](/images/zephyr/kernel/nanokernel/wait_q/2.png)</center>
<center>图 2. 等待队列的定义</center>

# 等待队列的初始化
```
static inline void _nano_wait_q_reset(struct _nano_queue *wait_q)
{
	wait_q->head = (void *)0;
	wait_q->tail = (void *)&(wait_q->head);
}

static inline void _nano_wait_q_init(struct _nano_queue *wait_q)
{
	_nano_wait_q_reset(wait_q);
}
```
进行队列结构体中成员的初始化：
- 将 head 成员指向 NULL。
- 将 tail 成员指向该队列自身(参考后面的图2)。

_nano_wait_q_init() 和 _nano_wait_q_reset() 是两个完全等价的函数。

对于如下程序：
```
struct _nano_queue wait_q;
_nano_wait_q_init(&wait_q);
```
其在内存空间的存储情况如图 3 所示。
<center>![](/images/zephyr/kernel/nanokernel/wait_q/3.png)</center>
<center>图 3. 等待队列的初始化</center>

# 在队尾插入线程
```
static inline void _nano_wait_q_put(struct _nano_queue *wait_q)
{
	((struct tcs *)wait_q->tail)->link = _nanokernel.current;
	wait_q->tail = _nanokernel.current;
}
```
很简单的两句话，但是理解起来蛮吃力的。我们分两种情况考虑：

## 当等待队列为空时插入线程

先回忆一下描述线程的结构体 struct cts 的定义：
```
struct tcs {
	struct tcs *link; 
	uint32_t flags;
	uint32_t basepri;
	int prio;
	
    ...
};
```
其在内存空间的存储情况如图 3 右边部分所示。我们需要注意其 link 成员，它是 struct tcs 的第一个成员，其类型是一个指向线程的指针。

当队列为空时，wait_q 的 tail 成员指向该队列自身的 head 成员，其结构如图 3 所示。((struct tcs *)wait_q->tail) 将 tail 强制转换为一个线程结构体指针，也就是说，tail 所指向的地址用于存放一个线程，而由于 link 是线程结构体 struct tcs 的第一个成员，且是一个指针，所以 ((struct tcs *)wait_q->tail)->link 的含义就是**有一个指针变量，该变量自身的地址等于 &wait_q->tail(即&wait_q->head), 该变量指向了一个线程的结构体**。

所以，((struct tcs *)wait_q->tail)->link = _nanokernel.current; 的含义就是将 head 指向当前正在执行的线程的结构体。

wait_q->tail = _nanokernel.current; 将 tail 也指向当前正在指向的线程的结构体。

对于如下程序：
```
struct _nano_queue wait_q;
_nano_wait_q_init(&wait_q);

_nano_wait_q_put(&wait_q);
```
其在内存空间的存储情况如图 3 所示。
<center>![](/images/zephyr/kernel/nanokernel/wait_q/4.png)</center>
<center>图 3. 队列为空时插入线程</center>

> 通常，当前正在执行的线程将自己加入到等待线程后，会调用函数 _swip() 释放 CPU，此时处于就绪状态的线程中的优先级最高的线程会占用 CPU 进行执行。

## 当等待队列不为空时插入线程

当等待队列不为空时，((struct tcs *)wait_q->tail) 表示等待队列的队尾线程，((struct tcs *)wait_q->tail)->link 表示对待队列的队尾线程的 link 成员。

((struct tcs *)wait_q->tail)->link = _nanokernel.current; 表示将队尾线程的 link 指向当前正在执行的线程的结构体。
wait_q->tail = _nanokernel.current; 表示将 tail 也指向当前正在执行的线程的结构体。

## 例子
对于如下代码：
```
struct _nano_queue wait_q;
_nano_wait_q_init(&wait_q);

//***********************************************************************************//
/* 线程 1 正在执行 */
...
_nano_wait_q_put(&wait_q); // 如图 4
...
/* 线程 1 释放 CPU */
//***********************************************************************************//
/* 线程 2 正在执行, 线程 1 已处于等待队列中 */
...
_nano_wait_q_put(&wait_q); // 如图 5
...
/* 线程 2 释放 CPU */
//***********************************************************************************//
/* 线程 3 正在执行, 线程 1/2 已处于等待队列中 */
...
_nano_wait_q_put(&wait_q); // 如图 6
...
/* 线程 3 释放 CPU */
//***********************************************************************************//

...

//***********************************************************************************//
/* 线程 6 正在执行, 线程 1/2/3/4/5 已处于等待队列中 */
...
_nano_wait_q_put(&wait_q); // 如图 7
...
/* 线程 6 释放 CPU */
```
<center>![](/images/zephyr/kernel/nanokernel/wait_q/4.png)</center>
<center>图 4.</center>

<center>![](/images/zephyr/kernel/nanokernel/wait_q/5.png)</center>
<center>图 5.</center>

<center>![](/images/zephyr/kernel/nanokernel/wait_q/6.png)</center>
<center>图 6.</center>

<center>![](/images/zephyr/kernel/nanokernel/wait_q/7.png)</center>
<center>图 7.</center>

# 在队首取出线程
```
struct tcs *_nano_wait_q_remove(struct _nano_queue *wait_q)
{
	return wait_q->head ? _nano_wait_q_remove_no_check(wait_q) : NULL;
}
```
先判断等待队列是否为空，如果为空，返回 NULL，如果不为空，调用函数_nano_wait_q_remove_no_check().
```
static struct tcs *_nano_wait_q_remove_no_check(struct _nano_queue *wait_q)
{
	// 获取等待队列的队首线程
	struct tcs *tcs = wait_q->head;

	if (wait_q->tail == wait_q->head) {
    	// 如果等待队列中只有一个线程了，对队列进行复位
		_nano_wait_q_reset(wait_q);
	} else {
    	// 如果队列中不止一个线程，将 head 指向第二个线程
		wait_q->head = tcs->link;
	}
	tcs->link = 0;

	// 将该线程加入就绪队列
	_nano_fiber_ready(tcs);
	return tcs;
}
```

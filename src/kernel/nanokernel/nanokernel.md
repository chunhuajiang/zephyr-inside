---
title: Zephys OS 内核篇：内核大总管 _nanokernel
date: 2016-08-04 13:39:33
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文介绍 Zephyr OS 中定义的全局变量 _nanokernel。
<!--more-->
在 Zephyr OS 中，定义了一个全局变量 _nanokernel，用于描述 nanokernel 的控制结构。_nanokernel 属于 Zephyr OS 中 BOSS 级别的人物，因此我们必须对这个领军人物做单独介绍。But，nanokernel 虽然属于 BOSS 级别，它的数据结构却不复杂。

# _nanokernel 的定义
nanokernel 定义于 arch/arm/core/thread.c：
```
tNANO _nanokernel = {0};
```
其数据类型 tNANO 的原型是：
```
typedef struct s_NANO tNANO
```
因此，我们最终要研究的数据结构是 struct s_NANO。

> 注意：由于 s_NANO 于具体芯片架构相关，所以在移植 Zephyr OS 时，需要考虑移植该结构。

```
struct s_NANO {
	struct tcs *fiber; 		
    struct tcs *task; 		
	struct tcs *current; 	
	int flags;  			

#if defined(CONFIG_THREAD_MONITOR)
	struct tcs *threads; 	
#endif

#ifdef CONFIG_FP_SHARING
	struct tcs *current_fp;	
#endif

#ifdef CONFIG_SYS_POWER_MANAGEMENT
	int32_t idle;    	
#endif

#if defined(CONFIG_NANO_TIMEOUTS) || defined(CONFIG_NANO_TIMERS)
	sys_dlist_t timeout_q;
	int32_t task_timeout; 
#endif
};
```
逐一解释各成员：
- fibler：所有 fiber 构成的单链表
- task：所有 task 构成的但链表
- current：指向当前正在被调用的线程(fiber 或 task)
- flags：当前正在被调度的线程的flags，等于 current->flags
- threads：内核中所有线程(fiber + task)构成的单链表
- current_fp：拥有 FP 寄存器的线程（fiber或task）构成的单链表。没懂。
- idle：内核空转的滴答数。不知道有啥作用。
- timeout_q：内核中的超时队列。具体信息请参考《Zephyr OS nano内核篇：超时服务 timeout》。
- task_timeout：于是与超时服务相关的，但是具体的含义还没弄明白。

可以看出，_nanokernel 这个大总管的成员几乎都是链表，通过这些链表可以找到所有的线程，进而再根据新城可以找到所有线程相关的信息，这就是内核大总管的超强能力！

# 线程的状态
Zephyr OS 中线程的状态可以分为三类：
- 执行态：指当前正在占用 CPU 执行任务的线程。由于物联网设备的低成本、低速率的特性，Zephyr OS 只支持单 CPU，因此内核中只有一个线程处于执行态。
- 就绪态：指已经准备就绪、等待被调度执行的线程，这些线程以优先级的顺序排列。当系统当前正在执行的线程执行完毕或进入等待队列时，调度算法会调度就绪态链表中优先级最高的线程。
- 等待态：当内核中的一个线程正在执行时，可能由于某种原因无法再执行下去(比如等待某种资源——信号量)，这时我们可以将该线程放入一个等待队列中，然后将 CPU 的执行权转交给其它线程，以达到最大效率使用 CPU 的目的。

线程的状态切换如图 1 所示。

<center>![](/images/zephyr/kernel/nanokernel/nanokernel/1.png)</center>

<center>图 1. 线程状态切换</center>


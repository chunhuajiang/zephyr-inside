---
title: Zephys OS 内核篇：初识线程
date: 2016-08-03 17:24:32
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文讲解 Zephyr OS 用于描述线程相关信息的结构体，内核中几乎其它所有服务都或多或少地使用了该结构体，所以在正式进入内核相关部分的学习之前，我们先学习该结构体。此外，还介绍了一下如何新建一个线程。

- [线程结构体的定义](#线程结构体的定义)
- [创建一个新线程](#创建一个新线程)
- [退出一个线程](#退出一个线程)
- [线程的本质](#线程的本质)

<!--more-->

# 线程结构体的定义
在 Zephyr OS 中，用结构体 struct tcs 描述一个线程的控制信息：

```
struct tcs {
	struct tcs *link;
	uint32_t flags;
	uint32_t basepri;
	int prio;
#ifdef CONFIG_THREAD_CUSTOM_DATA
	void *custom_data;
#endif
	struct coop coopReg;
	struct preempt preempReg;
#if defined(CONFIG_THREAD_MONITOR)
	struct __thread_entry *entry;
	struct tcs *next_thread;
#endif
#ifdef CONFIG_NANO_TIMEOUTS
	struct _nano_timeout nano_timeout;
#endif
#ifdef CONFIG_ERRNO
	int errno_var;
#endif
#ifdef CONFIG_MICROKERNEL
	void *uk_task_ptr;
#endif
};
```


> 注意：由于该结构体涉及到芯片的寄存器，所以不同架构的芯片的线程控制结构体是有区别的。本文讨论cortex-m3 的线程控制结构。另外，由于与具体芯片相关，所以将 Zephyr OS 移植到其它架构的芯片时，需要考虑移植线程相关的代码。

- link：多个线程可以构成一个线程链表，link 就指向该链表中的下一个线程。例如，处于就绪状态的线程会形成一个就绪队列，等待线程会形成一个等待队列，具体信息请参考《Zephyr OS nano 内核篇： fiber》和《Zephyr OS nano 内核篇：等待队列 wait_q》
- flags：用来表示该线程具有哪些 flag，这些 flag 是系统预定义的位掩码。
> 所谓的位掩码，是指每个每个掩码占 1 位。
> ```
> #define FIBER 0x000         // BIT(0) 为 0 表示该线程是 fiber
#define TASK  0x001	        // BIT(0) 为 1 表示该线程是 task
#define INT_ACTIVE 0x002    // BIT(1) 为 1 表示执行上下文是中断 handler
#define EXC_ACTIVE 0x004    // BIT(2) 为 1 表示执行上下文是异常
#define USE_FP 0x010	    // BIT(4) 为 1 表示该线程使用浮点单元
#define PREEMPTIBLE  0x020  // BIT(5) 为 1 表示该线程可被抢占。
           /*
	       * NOTE: the value must be < 0x100 to be able to \
	       *       use a small thumb instr with immediate  \
	       *       when loading PREEMPTIBLE in a GPR       \
	       */
#define ESSENTIAL 0x200    // BIT(9) 为 1 表示该线程不能被终止
#define NO_METRICS 0x400   // BIT(10)为 1 表示_Swap() not to update task metrics
> ```

- basepri：用于上下文切换时的现场保存与恢复。具体信息请参考《Zephyr OS nano 内核篇： 上下文切换》。
- prio：指定本线程的优先级。就绪链表中的线程就是按照优先级的顺序排列的。
- custom_data：线程自定义数据。
- coopReg：对于 Cortex-M 系列，该变量没有使用。
- preempReg：也是用于上下文切换时的现场保存与恢复。
> ```
> struct preempt {
	uint32_t v1;  /* r4 */
	uint32_t v2;  /* r5 */
	uint32_t v3;  /* r6 */
	uint32_t v4;  /* r7 */
	uint32_t v5;  /* r8 */
	uint32_t v6;  /* r9 */
	uint32_t v7;  /* r10 */
	uint32_t v8;  /* r11 */
	uint32_t psp; /* r13 */
};
> ```

- entry：函数指针，指向线程的入口函数(即线程的执行体)和参数，当线程被调用时候将调用该函数。
> ```
> struct __thread_entry {
> 	_thread_entry_t pEntry; // 指向线程的入口函数
	void *parameter1;		// 指向入口函数的第一个参数 arg1
	void *parameter2;		// 指向入口函数的第二个参数 arg2
	void *parameter3;		// 指向入口函数的第三个参数 arg3
};
// 线程的入口函数的函数原型
typedef void (*_thread_entry_t)(_thread_arg_t arg1,
							    _thread_arg_t arg2,
							    _thread_arg_t arg3);
> ```

- next_thread：与 link 类似，指向线程构成的链表中的下一个线程。不过 next_thread 指向的链表是由内核中所有的 fiber 和 task 构成的链表。
- nano_timeout：指定该线程所绑定的超时服务。关于超时服务，请参考《Zephyr OS nano  内核篇：超时服务 timeout》
- errno_var：错误号。
- uk_task_ptr：与microkernel相关，目前还不知道是干嘛的。

# 创建一个新线程
```
void _new_thread(char *pStackMem, unsigned stackSize,
		 void *uk_task_ptr, _thread_entry_t pEntry,
		 void *parameter1, void *parameter2, void *parameter3,
		 int priority, unsigned options)
{
	char *stackEnd = pStackMem + stackSize;
	struct __esf *pInitCtx;
	struct tcs *tcs = (struct tcs *) pStackMem;

#ifdef CONFIG_INIT_STACKS
	// 初始化线程栈的内容，让其每个字节都被初始化为0xaa。
    // 如果不初始化，则栈帧中被填充为0x00，这是为什么？
    //     因为线程栈的本质是一个全局变量，而全局变量默认被初始化为0
    // 如何知道线程栈的本质是一个全局变量？
    //     追踪代码，查看调用_new_thread 的地方，看看传进来的参数不就知道了么！
	memset(pStackMem, 0xaa, stackSize);
#endif
	// STACK_ROUND_DOWN(pointer) 的作用请参考【说明1】
    // pInitCtx 用来保存栈帧的信息，即线程的上下文信息，请参考【说明2】
	pInitCtx = (struct __esf *)(STACK_ROUND_DOWN(stackEnd) -
				    sizeof(struct __esf));
	pInitCtx->pc = ((uint32_t)_thread_entry) & 0xfffffffe;
	pInitCtx->a1 = (uint32_t)pEntry;
	pInitCtx->a2 = (uint32_t)parameter1;
	pInitCtx->a3 = (uint32_t)parameter2;
	pInitCtx->a4 = (uint32_t)parameter3;
	pInitCtx->xpsr =
		0x01000000UL; /* clear all, thumb bit is 1, even if RO */

	// 初始化 link、flag和prio
	tcs->link = NULL;
	tcs->flags = priority == -1 ? TASK | PREEMPTIBLE : FIBER;
	tcs->prio = priority;

#ifdef CONFIG_THREAD_CUSTOM_DATA
	tcs->custom_data = NULL;
#endif

#ifdef CONFIG_THREAD_MONITOR
	// 指定线程的入口函数和参数
	tcs->entry = (struct __thread_entry *)(pInitCtx);
#endif

#ifdef CONFIG_MICROKERNEL
	tcs->uk_task_ptr = uk_task_ptr;
#else
	ARG_UNUSED(uk_task_ptr);
#endif

	tcs->preempReg.psp = (uint32_t)pInitCtx;
	tcs->basepri = 0;

	// 初始化超时服务，具体信息请参考《Zephyr OS nano 内核篇：超时服务 timeout》
	_nano_timeout_tcs_init(tcs);

	/* initial values in all other registers/TCS entries are irrelevant */

	THREAD_MONITOR_INIT(tcs);
}

```
先看一下主要的入参：
- pStackMem：指定线程栈的起始地址
- stackSize：指定线程栈的大小
- pEntry：指定线程的入口函数的地址
- parameter1、parameter2、parameter3：指定传递给入口函数的参数。
- 其它：其它一些线程相关的设置，不影响我们理解线程的本质

_new_thread() 的主要任务：
- 为线程分配一段栈空间(其实是调用_new_thread()的函数分配的)。
- 为线程指定一个入口函数以及它的参数。
- 对线程栈进行初始化，包括：
 - 在线程栈的低地址处，存储一个结构体 struct tcs，用来保存线程的控制信息。
 - 在线程栈的高地址处，存储一个结构体 struct __esf，用来保存线程的上下文。

用一张图可以很好地总结这个函数：

<center>![](/images/zephyr/kernel/nanokernel/thread/stack.png)</center>

<center>线程栈的内存分布图</center>


然后再看看本函数的最后一条语句 THREAD_MONITOR_INIT(tcs) ，它涉及到内核中的一个线程链表。
```
#define THREAD_MONITOR_INIT(tcs) _thread_monitor_init(tcs)

static ALWAYS_INLINE void _thread_monitor_init(struct tcs *tcs /* thread */
					   )
{
	unsigned int key;

	key = irq_lock();
	tcs->next_thread = _nanokernel.threads;
	_nanokernel.threads = tcs;
	irq_unlock(key);
}
```
_nanokernel 是我们下一节《Zephyr OS nano 内核篇：内核大总管_nanokernel》的主角，是内核中定义的一个全局变量。它有一个成员 threads，指向内核中所有线程构成的一个单链表。

_thread_monitor_init() 的作用是将线程加入到该链表的表头。

关于内核中的线程构成的各种链表，请参考《Zephyr OS nano 内核篇：总结》。

【说明1】

STACK_ROUND_DOWN(x)和STACK_ROUND_UP(x)这对宏的作用是确保栈空间是 STACK_ALIGN_SIZE 字节对齐的。

当 x 表示栈空间的高地址时，需要调用 STACK_ROUND_DOWN(x) 以确保 x 是 STACK_ALIGN_SIZE 字节对齐的，它的主要思想如下：
- 如果 x 本来就是 STACK_ALIGN_SIZE 字节对齐的，则不做如何处理
- 如果 x 不是 STACK_ALIGN_SIZE 字节对齐的，它会舍弃高地址的 0 ~ (STACK_ALIGN_SIZE - 1) 字节，以确保 x 是 STACK_ALIGN_SIZE 字节对齐的。

当 x 表示栈空间的低地址时，需要调用 STACK_ROUND_UP(x) 以确保 x 是 STACK_ALIGN_SIZE 字节对齐的，它的主要思想与 STACK_ROUND_DOWN(x) 类似。

【说明2】

在《Zephyr OS 内核篇：上下文》一文中，我们已经知道，Zephyr 中的上下文分为三种：fiber、task 和中断，但是对于上下文具体值的什么，我们还不清楚。

个人理解，所谓的上下文指的就是线程在运行时芯片内部的环境，即芯片中相关寄存器的值。通过这些寄存器的值，能唯一确定一个线程的运行。那么，哪些因素将确定一个唯一的线程呢?

对于 Cortex-M 系列，内核定义了如下结构体来保存上下文的寄存器：
```
struct __esf {
	//sys_define_gpr_with_alias 用来定义成员的别名，其本质就是一个联合体
	sys_define_gpr_with_alias(a1, r0);
	sys_define_gpr_with_alias(a2, r1);
	sys_define_gpr_with_alias(a3, r2);
	sys_define_gpr_with_alias(a4, r3);
	sys_define_gpr_with_alias(ip, r12);
	sys_define_gpr_with_alias(lr, r14);
	sys_define_gpr_with_alias(pc, r15);
	uint32_t xpsr;
#ifdef CONFIG_FLOAT
	float s[16];
	uint32_t fpscr;
	uint32_t undefined;
#endif
};
```
其中，
- a1：用来保存线程入口函数的地址。
- a2：用来保存线程入口函数的第一个参数的值。
- a3：用来保存线程入口函数的第二个参数的值。
- a4：用来保存线程入口函数的第三个参数的值。
- ip：不知。。。
- lr：用来保存线程返回时的地址。
- pc：当线程执行到一半时，可能被切换出去(比如时间片到期了)，而 pc 指针就可以用来保存被切换出去时的地址。
- xpsr：用来保存线程当前的状态。

> 总结，用来保存线程上下文的变量包括：
> - struct __esf 中的r0,r1,r2,r3,r12,r14,r15,xpsr
> - struce tcs 中的 struct preempt 中的r4,r5,r6,r7,r8,r9,r10,r11,r13
> - struct tcs 中的 basepri
> 
> 即保存的寄存器现场包括：r0-r15, xpsr, basepri

# 退出一个线程
```
void _thread_exit(struct tcs *thread)
{
	if (thread == _nanokernel.threads) {
		// 如果该线程是链表中的头结点，直接删除之
		_nanokernel.threads = _nanokernel.threads->next_thread;
	} else {
		// 如果该线程不是链表中的头结点，先查找到该节点，再删除之
		struct tcs *prev_thread;

		prev_thread = _nanokernel.threads;
		while (thread != prev_thread->next_thread) {
			prev_thread = prev_thread->next_thread;
		}
		prev_thread->next_thread = thread->next_thread;
	}
}
```
将线程从 _nanokernel.threads 指向的线程链表中删除。

# 线程的本质
我们可以从逻辑上将线程看成两部分：
- 线程的执行实体，即线程的入口函数
- 线程栈




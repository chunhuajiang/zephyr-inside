---
title: Zephys OS 内核篇：线程模型
date: 2016-08-03 17:24:32
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文讲解 Zephyr OS 用于描述线程相关信息的结构体，内核中几乎其它所有服务都或多或少地使用了该结构体，所以在正式进入内核相关部分的学习之前，我们先学习该结构体。

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

- link：多个线程可以构成一个线程链表，link 就指向该链表中的下一个线程。例如，内核中的所有等待线程会形成一个等待队列，具体信息请参考《Zephyr OS nano 内核篇：等待队列 wait_q》
- flags：用来表示该线程具有哪些 flag，这些flag 是系统预定义的位掩码。


> 所谓的位掩码，是指每个每个掩码占 1 位。
>
> ```
#define FIBER 0x000         // BIT(0) 为 0 表示该线程是 fiber
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
```

- basepri：看名字应该是用于描述中断的基本优先级，即低于该优先级的中断将被屏蔽，高于等于该优先级的中断没被屏蔽。
- prio：指定本线程的优先级。就绪链表中的线程就是按照优先级的顺序排列的。
- custom_data：线程自定义数据。
- coopReg：对于 Cortex-M 系列，该变量没有使用。
- preempReg：目前没看出有啥用。
- entry：函数指针，指向线程的入口函数(即线程的执行体)和参数，当线程被调用时候将调用该函数。

> ```
> struct __thread_entry {
	_thread_entry_t pEntry; // 指向线程的入口函数
	void *parameter1;		// 指向入口函数的第一个参数 arg1
	void *parameter2;		// 指向入口函数的第二个参数 arg2
	void *parameter3;		// 指向入口函数的第三个参数 arg3
};
>  // 线程的入口函数的函数原型
typedef void (*_thread_entry_t)(_thread_arg_t arg1,
							    _thread_arg_t arg2,
							    _thread_arg_t arg3);
> ```

- next_thread：与 link 类似，指向线程构成的链表中的下一个线程。不过 next_thread 指向的链表是由内核中所有的fiber和task构成的链表。
- nano_timeout：指定该线程所绑定的超时服务。关于超时服务，请参考《Zephyr OS nano 内核篇：超时服务 timeout》
- errno_var：错误号。
- uk_task_ptr：

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
	memset(pStackMem, 0xaa, stackSize);
#endif

	/* carve the thread entry struct from the "base" of the stack */

	pInitCtx = (struct __esf *)(STACK_ROUND_DOWN(stackEnd) -
				    sizeof(struct __esf));

	pInitCtx->pc = ((uint32_t)_thread_entry) & 0xfffffffe;
	pInitCtx->a1 = (uint32_t)pEntry;
	pInitCtx->a2 = (uint32_t)parameter1;
	pInitCtx->a3 = (uint32_t)parameter2;
	pInitCtx->a4 = (uint32_t)parameter3;
	pInitCtx->xpsr =
		0x01000000UL; /* clear all, thumb bit is 1, even if RO */

	tcs->link = NULL;
	tcs->flags = priority == -1 ? TASK | PREEMPTIBLE : FIBER;
	tcs->prio = priority;

#ifdef CONFIG_THREAD_CUSTOM_DATA
	/* Initialize custom data field (value is opaque to kernel) */

	tcs->custom_data = NULL;
#endif

#ifdef CONFIG_THREAD_MONITOR
	/*
	 * In debug mode tcs->entry give direct access to the thread entry
	 * and the corresponding parameters.
	 */
	tcs->entry = (struct __thread_entry *)(pInitCtx);
#endif

#ifdef CONFIG_MICROKERNEL
	tcs->uk_task_ptr = uk_task_ptr;
#else
	ARG_UNUSED(uk_task_ptr);
#endif

	tcs->preempReg.psp = (uint32_t)pInitCtx;
	tcs->basepri = 0;

	_nano_timeout_tcs_init(tcs);

	/* initial values in all other registers/TCS entries are irrelevant */

	THREAD_MONITOR_INIT(tcs);
}

```
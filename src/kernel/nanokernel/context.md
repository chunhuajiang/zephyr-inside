---
title: Zephyr OS 内核篇： 执行上下文
date: 2016-07-28 16:45:35
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文简要介绍一下 Zephyr OS 执行上下文的基本概念以及相关的 API，这是后面学习的基础。

- [上下文的概念](#上下文的概念)
- [上下文类型的定义](#上下文类型的定义)
- [上下文相关的 API](#上下文相关的-api)
    - [sys_thread_self_get()](#sys_thread_self_get)
    - [sys_execution_context_type_get()](#sys_execution_context_type_get)
    - [sys_thread_custom_data_set()](#sys_thread_custom_data_set)
    - [sys_thread_custom_data_get()](#sys_thread_custom_data_get)
    - [sys_thread_busy_wait](#sys_thread_busy_wait)

<!--more-->
# 上下文的概念

在 Zephyr OS 中，存在三种类型的执行上下文：

- **task 上下文**：task 上下文是一个可抢占的、基于优先级的线程，主要用于处理执行时间长或者比较复杂工作。task 的调度是基于优先级的，所以高优先级的 task 可以抢占低优先级的 task。Zephyr 内核支持一个可选的循环时间片功能，因此相同优先级的 task 将轮流执行，从而可以避免了某个 task 独占 CPU 的风险。
- **fiber 上下文**：fiber 是一个轻量级的、不可抢占的、基于优先级的线程，主要用于设备驱动和对性能比较挑剔的工作。fiber 也是基于优先级的，因此高优先级的 fiber 比低优先级的 fiber 先被调度。不过，一个 fiber 一旦被调度，它将一直执行下去，直到它执行某个操作阻塞了自身的运行。fiber 的优先级比 task 高，因此只有在没有 fiber 的时候才会执行 task。
- **中断上下文**：中断上下文是一个特殊的上下文，用于执行中断服务程序 ISR。中断上下文的优先级比其它两种上下文的优先级都要高，所以只有在没有 ISR 时才有执行 fiber 和 task。

其中，task 和 fiber 是线程的两种不同表现形式，但是使用相同的线程相关的数据结构和函数接口。

所有的 task 和 fiber 都有一个唯一的*线程标识符*，用来唯一标识该线程。每个 task 和 fiber 也支持一个 32 位的*线程自定义数据*。线程自定义数据只能被 task 和 fiber 自己访问，可以被应用程序由于任何目的。默认情况下，该值为 0。

> ISR 中不存在自定义数据，因为 ISR 的操作只存在共享内核中断处理上下文中。

# 上下文类型的定义
Zephyr OS 中，上下文的类型定义如下：
```
typedef int nano_context_type_t;	// 定义上下文的类型

#define NANO_CTX_ISR   (0)			// 中断上下文
#define NANO_CTX_FIBER (1)			// fiber 上下文
#define NANO_CTX_TASK  (2)			// task 上下文
```

# 上下文相关的 API

执行上下文对外暴露了如下 API：
- **sys_thread_self_get**：获取当前正在执行的线程的线程标识符。
- **sys_execution_context_type_get**：获取当前正在执行的上下文的上下文类型。
- **sys_thread_custom_data_set**：设置当前正在执行的上下文的自定义数据。
- **sys_thread_custom_data_get**：获取当前正在执行的上下文的sys_thread_busy_wait自定义数据。
- **sys_thread_busy_wait**：设置当前正在执行的上下文的忙等待时间。

## sys_thread_self_get()
```
nano_thread_id_t sys_thread_self_get(void)
{
	return _nanokernel.current;
}
```
该函数用于获取当前正在执行的task或者fiber的线程标识符。

**nano_thread_it_t**：返回值类型 nano_thread_it_t 定义了线程标识符的类型，其原型是 struct tcs *。struct tcs * 用于描述线程的控制结构，将在下一篇《Zephyr OS 内核篇：线程模型》中介绍。

**_nanokernel.current**：_nanokernel 是 Zephyr OS 定义的一个描述超微内核的全局变量，其 current 成员表示当前正在执行的上下文的线程控制结构。_nanokernel 将在《Zephyr OS 内核篇：nanokernel》中介绍。

## sys_execution_context_type_get()

```
nano_context_type_t sys_execution_context_type_get(void)
{

	if (_IS_IN_ISR())
		return NANO_CTX_ISR;

	// 不是 ISR
	if ((_nanokernel.current->flags & TASK) == TASK)
		return NANO_CTX_TASK;

	// 既不是 ISR，又不是 task，当前上下文就是 fiber。
	return NANO_CTX_FIBER;
}
```

该函数用于返回当前正在执行的上下文的类型：task，fiber或者是 ISR。其函数实现如下：

**_IS_IN_ISR**：通过读取 IPSR 寄存器的值来判断当前上下文是否是 ISR。在 Cortex-M3 中，IPSR 的全称是 Interrupt Program Status Register，即中断程序状态寄存器，保存了当前中断的状态。相关信息可参考数据《Cortex-M3 权威指南》的第二章。

**_nanokernel.current->flags**：flags 记录了当前正在执行的上下文的一些标志信息，其具体描述请参考《Zephyr OS 内核篇：线程模型》。

## sys_thread_custom_data_set()
```
void sys_thread_custom_data_set(void *value)
{
	_nanokernel.current->custom_data = value;
}
```
该函数用于设置当前上下文线程自定义数据。

## sys_thread_custom_data_get()

```
void *sys_thread_custom_data_get(void)
{
	return _nanokernel.current->custom_data;
}
```
该函数返回当前上下文的线程自定义数据。
## sys_thread_busy_wait

```
void sys_thread_busy_wait(uint32_t usec_to_wait)
{
	uint32_t cycles_to_wait = (uint32_t)(
		(uint64_t)usec_to_wait *
		(uint64_t)sys_clock_hw_cycles_per_sec /
		(uint64_t)USEC_PER_SEC
	);
	uint32_t start_cycles = sys_cycle_get_32();

	for (;;) {
		uint32_t current_cycles = sys_cycle_get_32();

		// 有个疑问：cycle 可能溢出，但似乎没考虑到。
		if ((current_cycles - start_cycles) >= cycles_to_wait) {
			break;
		}
	}
}

```

> 内核允许 task 或者 fiber 执行**忙等待服务**，即延迟一段指定的时间，且在这段时间内该线程一直占用 CPU。此外，内核还提供了另一种延迟的方法——定时器(超时服务)。定时器(超时服务)会让当前线程在执行延迟时释放 CPU，让其它线程抢占 CPU 处理相关工作，并在延迟时间到期后自动切换到该线程。更多信息请参考《Zephyr OS nano 内核篇：超时服务 timeout》、《Zephyr OS nano 内核篇：定时器 Timer》和《Zephyr OS nano 内核篇：SysTick》。
> 
> 当程序需要进行延，但延迟的时间又很短而不能切换到其它 task 或者 fiber 的时候，就可以使用忙等待服务。在只使用超微内核的系统中，超微内核的后台 task 执行延迟时必须使用忙等待服务，因为这种 task 不允许主动放弃 CPU。

该函数用于设置当前上下文的忙等待时间。由于不用切换上下文，该函数的实现很简单：在一个“死”循环里，每循环一次就判断一下时间是否到期，如果没到期则继续循环，如果到期则退出循环。

**usec_to_wait**：输入参数，用于设置需要等待的时间，单位是微秒（microsecond）。

**cycles_to_wait**：将标准时间单位(ms)的输入参数usec_to_wait转换为硬件的时间单位(cycle)的cycles_to_wait。
> 注意，usec_to_wait 与 sys_clock_hw_cycles_per_sec 相乘时，会产生一个很大的数。
> 为了防止乘积溢出，先将其转换为uint64_t，待做完除法后再转回为 uint32_t。

**sys_cycle_get_32()**：该函数用于获取系统当前的硬件cycle数。





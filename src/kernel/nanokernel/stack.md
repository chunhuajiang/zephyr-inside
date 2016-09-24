---
title: Zephys OS nano 内核篇：栈 stack
date: 2016-09-24 11:49:33
categories: ["Zephyr OS"]
tags: [Zephyr]
---

栈是 nanokernel 提供的另一种用于在不同线程间传递数据的服务，它也是后进先出的，但是它与 lifo 的不同之处在于两点：

- 栈中的元素的大小是固定的，每个元素都是一个整型；lifo中的元素的数据的大小是不固定的
- 栈的内存空间是在栈的初始化时就固定了，里面保存的每个元素是实实在在的数据；lifo中保持的数据的内存空间是由向lifo中添加数据的线程分配的，所以lifo里面保存的是数据的指针。

# 栈的类型定义

```
struct nano_stack {
	nano_thread_id_t fiber;
	uint32_t *base;
	uint32_t *next;
#ifdef CONFIG_DEBUG_TRACING_KERNEL_OBJECTS
	struct nano_stack *__next;
#endif
};
```

不考虑用于调试的 __next，一共包含3个成员：

- fiber：一个栈允许一个线程在从栈中取数据时处于阻塞状态。fiber这个成员就用来保存这个阻塞的线程。
- base：指向栈底。
- next：指向栈中数据顶部的下一个地址，即栈空闲空间的底部，如下图所示。

栈结构体和栈在内存空间的存储情况如下图所示；



<center>

![](/images/zephyr/kernel/nanokernel/stack/1.png)



图：栈结构体与栈在内存空间的存储结构

</center>

# 栈的初始化

```
void nano_stack_init(struct nano_stack *stack, uint32_t *data)
{
	stack->next = stack->base = data;
	stack->fiber = (struct tcs *)0;
	SYS_TRACING_OBJ_INIT(nano_stack, stack);
}
```

初始化栈结构体中相关成员：将 base、next 指向栈底，将 fiber 指向 NULL。

# 出栈操作

```
int nano_stack_pop(struct nano_stack *stack, uint32_t *pData, int32_t timeout_in_ticks)
{
	static int (*func[3])(struct nano_stack *, uint32_t *, int32_t) = {
		nano_isr_stack_pop,
		nano_fiber_stack_pop,
		nano_task_stack_pop,
	};

	return func[sys_execution_context_type_get()](stack, pData, timeout_in_ticks);
}
```

先看看函数的入参：

- stack：待取数据的栈
- pData：用来保存从栈中取得的数据
- timeout_in_ticks：出栈的超时等待时间，以滴答为单位。函数内部会根据该变量的值来做相应的处理。

再看看函数的返回值：

- 1 - 表示出栈成功，即成功从栈中取得数据。
- 0 - 表示出栈失败，即没有从栈中取得数据。



nano_stack_pop会根据当前上下文的类型，调用对应的获取信号的函数。其中，nano_isr_stack_pop() 和 nano_fiber_stack_pop() 是函数 _stack_pop() 的别名。

## _stack_pop

```
int _stack_pop(struct nano_stack *stack, uint32_t *pData, int32_t timeout_in_ticks)
{
	unsigned int imask;

	imask = irq_lock();

	if (likely(stack->next > stack->base)) {
		// 如果栈中有数据，则直接从栈中取出：
		// 将 next 指针后移，指向数据的顶部
		// 然后取出数据，放入 pData 指向的内存处
		// 然后返回 1，表示出栈操作成功
		stack->next--;
		*pData = *(stack->next);
		irq_unlock(imask);
		return 1;
	}

	if (timeout_in_ticks != TICKS_NONE) {
		// 如果栈中没有数据，将当前线程(即正在执行出栈操作的线程)
		// 用栈中的 fiber 成员保存起来
		// 然后进行上下文切换
		stack->fiber = _nanokernel.current;
		*pData = (uint32_t) _Swap(imask);
		// 指向完 _Swap() 函数后，将会切换到其它上下文
		// 如果代码能走到这里，说明有其它线程向该栈中压入了数据，并唤醒了本线程
		// 将数据存放到 pData 指向的内存中
		// 然后返回 1，表示出栈操作成功
		return 1;
	}
	
	// 如果代码走到这里，说明执行操作操作的线程不希望进行延时等待
	// 此时出栈操作失败，立即返回
	irq_unlock(imask);
	return 0;
}
```

当某线程尝试从栈中弹出数据时，有两种可能：

- 栈中有数据，直接弹出数据顶部的数据
- 栈中没有数据，此时会根据入参 timeout_in_ticks 的值来做对应的处理：
  - 等于 TICKS_NONE，表示不进行超时等待，立即返回
  - 不等于 TICKS_NONE，将其陷入阻状态，并等待其它需要入栈的线程唤醒本线程

与前面所学的信号量、fifo、lifo都不同的是：

- 栈中没有设置等待队列，只用了一个fiber成员，最多只能保存一个阻塞线程，因此当多个线程都尝试向一个空栈中弹出数据时，只有最后一个线程能被保存，其它的线程将被替换掉，永远也无法获取数据(**而且最奇怪的是，这个线程好像也不处于就绪队列，将永远不会在被执行**)。为什么要这样设计？可能与栈的具体应用有关系，目前还不清楚。
- 当从栈中弹出数据失败时，没有将线程放入超时链表中，因此传入的参数 timeout_in_ticks **只要不等于 TICKS_NONE，将一直陷入阻塞**，直到有其它线程需要向栈中压入数据

## nano_task_stack_pop

```
int nano_task_stack_pop(struct nano_stack *stack, uint32_t *pData, int32_t timeout_in_ticks)
{
	unsigned int imask;

	imask = irq_lock();

	while (1) {
		if (likely(stack->next > stack->base)) {
			// 如果栈中有数据，则直接从栈中取出：
			// 将 next 指针后移，指向数据的顶部
			// 然后取出数据，放入 pData 指向的内存处
			// 然后返回 1，表示出栈操作成功
			stack->next--;
			*pData = *(stack->next);
			irq_unlock(imask);
			return 1;
		}

		if (timeout_in_ticks == TICKS_NONE) {
			// 如果 timeout_in_ticks 等于 TICKS_NONE，跳出循环，立即返回
			break;
		}
		
		// nano_cpu_atomic_idle() 函数已在《Zephyr OS nano 内核篇：信号量》中详
		// 细分析过，它会让cpu进入睡眠模式，如果发生外部中断，cpu会被唤醒。
		nano_cpu_atomic_idle(imask);
		imask = irq_lock();
	}

	irq_unlock(imask);
	return 0;
}
```



# 入栈操作

```
void nano_stack_push(struct nano_stack *stack, uint32_t data)
{
	static void (*func[3])(struct nano_stack *, uint32_t) = {
		nano_isr_stack_push,
		nano_fiber_stack_push,
		nano_task_stack_push
	};

	func[sys_execution_context_type_get()](stack, data);
}
```

先看看函数的入参：

- stack：待压入数据的栈。
- data：待压如栈中的数据，其数据类型是无符号整型。



nano_stack_push会根据当前上下文的类型，调用对应的获取信号的函数。其中，nano_isr_stack_push() 和 nano_fiber_stack_push() 是函数 nano_stack_push() 的别名。

##  _stack_push_non_preemptible

```
void _stack_push_non_preemptible(struct nano_stack *stack, uint32_t data)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();

	tcs = stack->fiber;
	if (tcs) {
		// 如果之前已有线程在等待从栈中取数据，直接设置将数据设置为该线程的返回值，
		// 然后将其从阻塞态变为就绪态，加入就绪链表
		stack->fiber = 0;
		fiberRtnValueSet(tcs, data);
		_nano_fiber_ready(tcs);
	} else {
		// 将数据压栈
		*(stack->next) = data;
		// next 指针上移
		stack->next++;
	}

	irq_unlock(imask);
}

```

注意，由于在入栈时没有检查栈是否已满，所以在使用时必须小心，否则栈溢出了，后果很严重。这算不算stack中的一个bug？

## nano_task_stack_push

```
void nano_task_stack_push(struct nano_stack *stack, uint32_t data)
{
	struct tcs *tcs;
	unsigned int imask;

	imask = irq_lock();

	tcs = stack->fiber;
	if (tcs) {
		// 如果之前已有线程在等待从栈中取数据，直接设置将数据设置为该线程的返回值，
		// 然后将其从阻塞态变为就绪态，加入就绪链表
		stack->fiber = 0;
		fiberRtnValueSet(tcs, data);
		_nano_fiber_ready(tcs);
		// 由于当前上下文是task，而就绪链表中存在fiber，所以就绪上下文切换
		_Swap(imask);
		return;
	}
	
	// 代码走到这里，说明之前没有程序在等待从栈中取数据，直接将数据入栈
	*(stack->next) = data;
	stack->next++;

	irq_unlock(imask);
}
```
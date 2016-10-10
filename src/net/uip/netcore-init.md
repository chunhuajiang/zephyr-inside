---
title: Zephys OS uIP 协议栈：net core - 初始化
date: 2016-10-11 19:55:27
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本节我们学习 net core 的初始化过程，即整个 uIP 协议栈的初始化过程，看看它都做了哪些事儿。

- [net_init](#net_init)
- [init_tx_queue](#init_tx_queue)
- [init_rx_queue](#init_rx_queue)
- [init_timer_fiber](#init_timer_fiber)
- [net_driver_xxxx_init](#net_driver_xxxx_init)
- [network_initialization](#network_initialization)
- [tcpip_set_outputfunc](#tcpip_set_outputfunc)

<!--more-->
# net_init
```
int net_init(void)
{
  // 如果已经被初始化了，直接返回错误码
	if (initialized)
		return -EALREADY;

  // 标志 uIP 协议栈已被初始化
	initialized = 1;

#if UIP_STATISTICS == 1
  // 如果定义了 uIP 的统计功能，初始化全局的统计变量
	memset(&uip_stat, 0, sizeof(uip_stat));
#endif /* UIP_STATISTICS == 1 */

  // 初始化 context
	net_context_init();

  // 初始化 ip_buf。上层协议，包括网络层、传输层、应用层都会使用这个 buf
	ip_buf_init();
  // 初始化 l2_buf。底层协议，包括 MAC 层、物理层都会使用这个 buf
	l2_buf_init();

  // 初始化 tx 队列。
	init_tx_queue();
  // 初始化 rx 队列。
	init_rx_queue();
  // 初始化 timer 线程。
	init_timer_fiber();

#if defined(CONFIG_NETWORKING_WITH_15_4)
  // 如果配置了 802.15.4 驱动，则进行其初始化
	net_driver_15_4_init();
#endif

#if defined(CONFIG_NETWORKING_WITH_BT)
  // 如果配置了bluetooth 驱动，则进行其初始化
	net_driver_bt_init();
#endif

  // 如果配置了 slip 驱动，则进行其初始化
	net_driver_slip_init();
  // 如果配置了以太网驱动，则进行其初始化
	net_driver_ethernet_init();

  // 进一步初始化协议栈
	return network_initialization();
}
```
# init_tx_queue
```
static void init_tx_queue(void)
{
  // 初始化 netdev 中绑定的 tx_queue
	nano_fifo_init(&netdev.tx_queue);

  // 新建一个 tx 线程 net_tx_fiber，该线程负责将 tx_queue 中的数据
  // 传送出去。该线程的具体内容，将在《net core - 发送数据》一节中
  // 详细介绍
	tx_fiber_id = fiber_start(tx_fiber_stack, sizeof(tx_fiber_stack),
				  (nano_fiber_entry_t)net_tx_fiber,
				  0, 0, 7, 0);
}
```
# init_rx_queue
```
static void init_rx_queue(void)
{
  // 初始化 netdev 中绑定的 rx_queue
	nano_fifo_init(&netdev.rx_queue);

  // 新建一个 rx 线程 net_rx_fiber，该线程将负责处理从底层驱动传上来的
  // 接收到的放于 rx_queue 中的数据。该线程的具体内容，将在《net core - 接收数据》
  // 一节中详细介绍
	fiber_start(rx_fiber_stack, sizeof(rx_fiber_stack),
		    (nano_fiber_entry_t)net_rx_fiber, 0, 0, 7, 0);
}
```
# init_timer_fiber
```
static void init_timer_fiber(void)
{
  // 新建了一个定时器线程 net_timer_fiber
	timer_fiber_id = fiber_start(timer_fiber_stack,
				     sizeof(timer_fiber_stack),
				     (nano_fiber_entry_t)net_timer_fiber,
				     0, 0, 7, 0);
}
```
```
static void net_timer_fiber(void)
{
	clock_time_t next_wakeup;

	while (1) {
		// 运行 Contiki 中的事件定时器线程，该线程内部会给所有到期的定时器所绑定的线程
    // 投递一个事件定时器事件，即运行到期定时器所绑定的线程
		next_wakeup = etimer_request_poll();
    // 该函数的返回值：
    // 0  - Contiki 的事件定时器链表中没有定时器了
    // >0 - Contiki 的事件定时器链表中还有定时器，且其中最近的一个定时器
    //      将在 next_wakeup 个滴答后到期
		if (next_wakeup == 0) {
      // 没有定时器了，直接睡眠最大值
			next_wakeup = MAX_TIMER_WAKEUP;
		} else {
			if (next_wakeup > MAX_TIMER_WAKEUP) {
        // 定时器的到期事件比预定义的最大值还大，则也睡眠最大值
				next_wakeup = MAX_TIMER_WAKEUP;
			}

#ifdef CONFIG_INIT_STACKS
    ...
#endif
		}

    // 睡眠 next_wakeup 个滴答后再被唤醒
		fiber_sleep(next_wakeup);
	}
}
```
# net_driver_xxxx_init
在 net_init() 函数中，初始化了四个底层设备：
- net_driver_15_4_init
- net_driver_bt_init
- net_driver_slip_init
- net_driver_ethernet_init

它们内部的实现都做了一件事儿：将其驱动程序绑定到 netdev 中。在前面我们已经学习过了，驱动程序以注册驱动的形式绑定到 netdev 上，且当 netdev 已经绑定了驱动程序后，后面再尝试绑定其它驱动将失败(除非先将绑定的驱动取消注册)，所以什么的四个初始化函数，只有第一个会初始化成功成功。

# network_initialization
```
static int network_initialization(void)
{
	// 初始化时钟
	clock_init();

  // 初始化 rtimer
	rtimer_init();
  // 初始化 ctimer
	ctimer_init();

  // 初始化 Contiki 的线程环境
	process_init();
  // 设置一个回调函数。这是一个枢纽点，单独说明
	tcpip_set_outputfunc(net_tcpip_output);

  // 启动线程 tcpip_process
	process_start(&tcpip_process, NULL, NULL);
  // 启动线程 simple_udp_process
	process_start(&simple_udp_process, NULL, NULL);
  // 启动线程 etimer_process
	process_start(&etimer_process, NULL, NULL);
  // 启动线程 ctimer_process
	process_start(&ctimer_process, NULL, NULL);

  ...

	return 0;
}
```
# tcpip_set_outputfunc
```
void tcpip_set_outputfunc(uint8_t (*f)(struct net_buf *buf, const uip_lladdr_t *))
{
  outputfunc = f;
}
```
额，看上去好简单。outputfunc 是 uIP 协议栈内部定义的一个函数指针，当发送数据时，协议栈内部对 buffer 中的数据进行填充后，会调用 outputfunc 这个函数指针，即执行 f() 这个函数。在上面的初始化过程中，传入的函数是 net_tcpip_output()，所以协议栈内部最终会调用 net_tcpip_output() 这个函数发送数据。

> 想知道协议栈内部是如何调用这个函数的？以 outputfunc 为关键字搜索整个工程，追踪相应的代码就知道了。不过其中的过程和复杂，我们会在今后学习上层协议的时候再讨论。

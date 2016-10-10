---
title: Zephys OS uIP 协议栈：由一个例子入手
date: 2016-10-10 18:33:14
categories: ["Zephyr OS"]
tags: [Zephyr]
---

为了从总体上把握 uIP 协议栈，我们通过一个例子作为一个引子，引出我们需要学习的内容。左挑右挑，最终选定了`samples/net/loopback`这个例程，因为它比较简单。

- [仿真](#仿真)
- [主函数](#主函数)
- [发送数据](#发送数据)
- [接收数据](#接收数据)
- [向前看](#向前看)
- [学习说明](#学习说明)

<!--more-->

# 仿真
这个 loopback 例程可以使用 qemu 进行仿真：
```
cd samples/net/loopback
make qemu
```
然后程序就跑起来了。

> 退出 qemu 的方法别忘了：先按 ctrl+a，再输入 X

# 主函数
```
void main(void)
{
	struct in6_addr in6addr_any = IN6ADDR_ANY_INIT;            /* ::  */
	struct in6_addr in6addr_loopback = IN6ADDR_LOOPBACK_INIT;  /* ::1 */

  // 后面要用到随机数函数，所以先初始化
	sys_rand32_init();

  // 初始化 uIP 协议栈
	net_init();
  // 注册 loopback 驱动
	net_driver_loopback_init();

  // any_addr 是本文件内定义的全局变量，表示一个 IPv6 地址
	any_addr.in6_addr = in6addr_any;
	any_addr.family = AF_INET6;

  // loopback 也是该文件定义的全局变量，表示一个地址
	loopback_addr.in6_addr = in6addr_loopback;
	loopback_addr.family = AF_INET6;

  // 创建接收线程
	receiver_id = task_fiber_start(receiver_stack, STACKSIZE,
				       (nano_fiber_entry_t)fiber_receiver,
				       0, 0, 7, 0);
  // 创建发送线程
	sender_id = task_fiber_start(sender_stack, STACKSIZE,
				     (nano_fiber_entry_t)fiber_sender,
				     0, 0, 7, 0);
}
```
总结起来，主要做了两件事儿：
- 初始化整个协议栈(一般情况下，注册驱动在 net_init 内部就完成了，不需要单独注册)。
- 创建了两个线程，一个发送数据，一个接收数据。

整个程序的数据思路：创建两个线程，一个发送数据，一个接收数据。发送线程设置好要发送的 buffer 后，调用协议栈提供的发送函数，然后该函数内部会调用 loopback 驱动，发送数据。同时，接收线程从 loopback 取出接收到的数据。

> 什么是 loopback？这是一个虚拟的网络接口。正常情况下，两台主机，一台主机发送数据，另一台主机接收数据。如果使用 loopback 这个虚拟接口，主机将数据发送该主机自己。使用 loopback 的好处是，它不需要底层(MAC 层和 PHY)芯片的支持，只使用一台主机就能测试协议栈的接口的功能。

# 发送数据
```
void fiber_sender(void)
{
	struct net_context *ctx;
	struct net_buf *buf;
	uint16_t sent_len;
	size_t len;
	int header_size;

  // 获取已给 context
  // 这里的 context 有点类似于 linux 的 socket
	ctx = net_context_get(IPPROTO_UDP, &loopback_addr, 4242, &any_addr, 0);
	if (!ctx) {
		return;
	}

	while (!failure) {
    // 通过获取的 context 获取 context 里面定义的 net buffer
		buf = ip_buf_get_tx(ctx);
		if (buf) {
      // 将要发送的数据拷贝到 buffer 里面
			prepare_to_send(buf, &len);
      // 设置 buf 中数据的长度
			sent_len = buf->len;
			header_size = ip_buf_reserve(buf);
			data_len = sent_len - header_size;
			ip_buf_appdatalen(buf) = data_len;

      // 调用 net core 提供的发送函数
			if (net_send(buf) < 0) {
				PRINT("[%d] %s: net_send failed!\n",
				      sent, __func__);
				failure = 1;
			}
      // 发送成功后，解除对 buffer 的引用
			ip_buf_unref(buf);
			sent++;
		}
    // 唤醒接收线程
		fiber_wakeup(receiver_id);
		fiber_sleep(SLEEPTICKS);
		if (sent != received) {
			failure = 1;
		}
		if (count && (count < sent)) {
			break;
		}
	}
}
```
核心要点：
- net_context_get：点类似于 linux 的 socket，在 context 中绑定发送者的 IP和端口、接收这的 IP 和端口。
- ip_buf_get_tx(ctx)：通过 context 获取其内部的发送 buffer，并对该 buffer 做一些初始化工作，比如根据 context 的内容向 buffer 中填充一些协议头。
- prepare_to_send：向 buffer 中填充数据。
- net_send：发送数据。
- ip_buf_unref：解除对 context 中该 buffer 的引用

# 接收数据
```
void fiber_receiver(void)
{
	struct net_context *ctx;
	struct net_buf *buf;
	char *rcvd_buf;
	int rcvd_len;

  // 获取接收 context
	ctx = net_context_get(IPPROTO_UDP, &any_addr, 0, &loopback_addr, 4242);
	if (!ctx) {
		return;
	}

	while (!failure) {
    // 调用 net core 提供的接收函数接收数据
		buf = net_receive(ctx, TICKS_UNLIMITED);
		if (buf) {
      /* 解析数据 */
      // 获取 buffer 数据的起始地址
			rcvd_buf = ip_buf_appdata(buf);
      // 取出数据的长度
			rcvd_len = ip_buf_appdatalen(buf);

      // 比较接收的数据与发送的数据是否相等。
			if (eval_rcvd_data(rcvd_buf, rcvd_len) != 0) {
				failure = 1;
			}
      // 解除对 context 中的 buffer 的引用
			ip_buf_unref(buf);
			received++;
		}
    // 唤醒发送线程
		fiber_wakeup(sender_id);
		fiber_sleep(SLEEPTICKS);
		if (count && (count < received)) {
			break;
		}
	}
}
```

核心要点：
- net_context_get：与 socket 类似，每个发送者、接收这都有自己的 context。
- net_receive：调用 net core 提供的接收函数，当接收到数据时，该函数返回 context 中接收 buffer 的地址。
- ip_buf_unref：解除对 context 中该 buffer 的引用

# 向前看
从这个简单的例子中，我们看到主要需要从以下几个方面入手：
- net core：这里面主要涉及整个协议栈的数据流向
- net context：这个，这个，真不好描述，，，反正它很重要
- buffer 管理：buffer 的重要性不言而喻，在 uIP 的整个协议栈，主要涉及到的 buffer 包括：
  - l2 buffer：底层协议(6lowpan, mac 协议)需要使用的 buffer
  - ip buffer：上层协议(网络层的协议)需要使用的 buffer

> l2 是什么意思？它的全称是 layer 2。在 TCP/IP 五层架构中，物理层、MAC 层、网络层、传输层和应用层被分别叫做 l1、l2、l3、l4 和 l5

今后，我们将根据这几个点入手，进一步研究协议栈。

# 学习说明

我们目前的主要目的是先弄清楚整个协议栈的架构，所以我们先挑软柿子捏：
- 传输层:我们只讨论 UDP，不讨论 TCP。
- 网络层：我们只讨论 IPv4，不讨论 IPv6。

此外，由于是先从总体上把握整个协议栈的架构，在学习这个架构的过程中，难免会碰到一些我们今后会才学习到的知识，此时我们不必拘泥于这些细节，而要不求甚解。当理解了整个架构后，我们再具体学习各层的内容，此时我们再研究这些细节。

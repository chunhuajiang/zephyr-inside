---
title: Zephys OS uIP 协议栈：netcore - 发送数据
date: 2016-10-11 22:39:19
categories: ["Zephyr OS"]
tags: [Zephyr]
---

这一节我们来学习 uIP 协议栈向网络发送数据的流程。

- [net_send](#net_send)
- [net_tx_fiber](#net_tx_fiber)
- [check_and_send_packet](#check_and_send_packet)
- [simple_udp_send](#simple_udp_send)
- [simple_udp_sendto](#simple_udp_sendto)
- [uip_udp_packet_sendto](#uip_udp_packet_sendto)
- [uip_udp_packet_send](#uip_udp_packet_send)
- [tcpip_output](#tcpip_output)
- [net_tcpip_output](#net_tcpip_output)

<!--more-->
# net_send
应用程序准备好要发送的 buffer 后，调用 net_send 函数就可以发送数据了，所以我们通过 net_send() 这个函数，追踪一下发送数据的整体流程。

```
int net_send(struct net_buf *buf)
{
	int ret = 0;

  // 先简单地对应用程序传入的 buf 进行有效性检查
	if (!buf || ip_buf_len(buf) == 0) {
		return -ENODATA;
	}
	if (buf->len && !uip_appdatalen(buf)) {
		uip_appdatalen(buf) = ip_buf_appdatalen(buf);
	}

  // (根据当前上下文来决定)释放 CPU，切换到其它线程
  // 有个疑问，为什么要切换？
	switch (sys_execution_context_type_get()) {
	case NANO_CTX_ISR:
		break;
	case NANO_CTX_FIBER:
		fiber_yield();
		break;
	case NANO_CTX_TASK:
#ifdef CONFIG_MICROKERNEL
		task_yield();
#endif
		break;
	}

#ifdef CONFIG_NETWORKING_WITH_TCP
	......
#endif

  // 将该 buffer 放到 netdev 的 tx_queue 中
	nano_fifo_put(&netdev.tx_queue, buf);

	// 唤醒发送线程
	fiber_wakeup(tx_fiber_id);

	return ret;
}
```
对于 UDP 来说，上面的代码基本没对 buf 做如何处理，直接将其放到 netdev 的 tx_queue 中，然后唤醒发送线程。
# net_tx_fiber
```
static void net_tx_fiber(void)
{
	while (1) {
		struct net_buf *buf;
		int ret;

		// 从 netdev 的 tx_queue 中取 buffer
    // 这里传入的参数为 TICKS_UNLIMITED
    // 表示如果此时 tx_queue 中没有 buffer，该线程将加入阻塞状态，直到 net_send() 向
    // tx_queue 中放了 buffer，然后把该线程唤醒
		buf = net_buf_get_timeout(&netdev.tx_queue, 0, TICKS_UNLIMITED);

    // 代码走到这里，说明已经成功取到 buffer 了。

		/* 根据返回值，判断对 buffer 的操作：
		 *  <0: 发生了错误，我们需要释放 buffer
		 *   0: 消息被 uIP 协议栈丢弃了， 此时 buffer 已被 uIP 释放了
		 *  >0: 消息发送成功，buffer 已被释放
		 */
		ret = check_and_send_packet(buf);
		if (ret < 0) {
			ip_buf_unref(buf);
			goto wait_next;
		} else if (ret > 0) {
			goto wait_next;
		}

		NET_BUF_CHECK_IF_NOT_IN_USE(buf);

		// 处理完我们需要处理的所有事件
		do {
			ret = process_run(buf);
		} while (ret > 0);

		// 释放 buffer
		ip_buf_unref(buf);

	wait_next:
	  ...
	}
}
```

# check_and_send_packet
```
static int check_and_send_packet(struct net_buf *buf)
{
	struct net_tuple *tuple;
	struct simple_udp_connection *udp;
	int ret = 0;

	if (!netdev.drv) {
		// 如果 netdev 没有绑定驱动，直接返回错误，因为我们 buf 中的数据需要驱动程序发送到信道中
		return -EINVAL;
	}

	tuple = net_context_get_tuple(ip_buf_context(buf));
	if (!tuple) {
		return -EINVAL;
	}

	// 根据 context 中设定的 协议，做相应的处理。
	switch (tuple->ip_proto) {
		case IPPROTO_UDP:
			udp = net_context_get_udp_connection(ip_buf_context(buf));

			// 判断该buf 所在的 context 是否进行了 udp 注册
			if (!net_context_get_receiver_registered(ip_buf_context(buf))) {
				// 如果没有进行 udp 注册，则先进行 udp 注册
				ret = simple_udp_register(udp, tuple->local_port,
	#ifdef CONFIG_NETWORKING_WITH_IPV6
					(uip_ip6addr_t *)&tuple->remote_addr->in6_addr,
	#else
					(uip_ip4addr_t *)&tuple->remote_addr->in_addr,
	#endif
					tuple->remote_port, udp_packet_reply,
					ip_buf_context(buf));
				if (!ret) {
					ret = -ENOENT;
					break;
				}
				// 设置“已注册”标志
				net_context_set_receiver_registered(ip_buf_context(buf));
			}

			if (ip_buf_appdatalen(buf) == 0) {
				// 应用程序没有设置上层 buf 中的数据长度(不包括IP/UDP/协议头)
				uip_appdatalen(buf) = buf->len - (UIP_IPUDPH_LEN + UIP_LLH_LEN);
			}

			ret = simple_udp_send(buf, udp, uip_appdata(buf),uip_appdatalen(buf));
			break;
	case IPPROTO_TCP:
#ifdef CONFIG_NETWORKING_WITH_TCP
		......
#endif
		break;
	case IPPROTO_ICMPV6:
		NET_DBG("ICMPv6 not yet supported\n");
		ret = -EINVAL;
		break;
	}

	return ret;
}
```
# simple_udp_send
```
int simple_udp_send(struct net_buf *buf, struct simple_udp_connection *c,
                const void *data, uint16_t datalen)
{
  if(c->udp_conn != NULL) {
    return uip_udp_packet_sendto(buf, c->udp_conn, data, datalen,
                          &c->remote_addr, UIP_HTONS(c->remote_port));
  }
  return 0;
}
```
没啥可说的，继续追踪代码。
# simple_udp_sendto
```
int simple_udp_sendto(struct net_buf *buf, struct simple_udp_connection *c,
                  const void *data, uint16_t datalen,
                  const uip_ipaddr_t *to)
{
  if(c->udp_conn != NULL) {
    return uip_udp_packet_sendto(buf, c->udp_conn, data, datalen,
                          to, UIP_HTONS(c->remote_port));
  }
  return 0;
}
```
继续追踪代码。
# uip_udp_packet_sendto
```
uint8_t uip_udp_packet_sendto(struct net_buf *buf, struct uip_udp_conn *c, const void *data, int len,
		      const uip_ipaddr_t *toaddr, uint16_t toport)
{
  uip_ipaddr_t curaddr;
  uint16_t curport;
  uint8_t ret = 0;

  if(toaddr != NULL) {
		......
    ret = uip_udp_packet_send(buf, c, data, len);
		.....
  }

  return ret;
}
```
# uip_udp_packet_send
```
uint8_t uip_udp_packet_send(struct net_buf *buf, struct uip_udp_conn *c, const void *data, int len)
{
#if UIP_UDP
  if(data != NULL) {
    uip_set_udp_conn(buf) = c;
    uip_slen(buf) = len;
    memcpy(&uip_buf(buf)[UIP_LLH_LEN + UIP_IPUDPH_LEN], data,
           len > UIP_BUFSIZE - UIP_LLH_LEN - UIP_IPUDPH_LEN?
           UIP_BUFSIZE - UIP_LLH_LEN - UIP_IPUDPH_LEN: len);
		// 在 uip_process 内部，添加 ip/udp 的协议头，我们先不分析
    if (uip_process(&buf, UIP_UDP_SEND_CONN) == 0) {
      /* The packet was dropped, we can return now */
      return 0;
    }

#if UIP_CONF_IPV6_MULTICAST
	......
#endif /* UIP_IPV6_MULTICAST */

 if (!uip_len(buf)) {
   /* Message was successfully sent, just bail out now. */
   goto out;
 }

#if NETSTACK_CONF_WITH_IPV6
		......
#else
    if(uip_len(buf) > 0) {
			// 将 buf 中的数据发送出去！！！！
      tcpip_output(buf, NULL);
    }
#endif
  }
out:
  uip_slen(buf) = 0;
#endif /* UIP_UDP */
  return 1;
}
```
终于到了终点，可以看看 buf 中的数据是如何发送出去的了！！
# tcpip_output
```
uint8_t tcpip_output(struct net_buf *buf, const uip_lladdr_t *a)
{
  if(outputfunc != NULL) {
    return outputfunc(buf, a);
  }
  UIP_LOG("tcpip_output: Use tcpip_set_outputfunc() to set an output function");
  return 0;
}
```
额，outputfunc 是什么东西？它是我们在进行 协议栈初始化时设置的一个函数指针。回忆一下 network_initialization() 函数里面，它有这么一句话：
```
tcpip_set_outputfunc(net_tcpip_output);
```
而 tcpip_set_outputfunc 的实现如下：
```
void tcpip_set_outputfunc(uint8_t (*f)(struct net_buf *buf, const uip_lladdr_t *))
{
  outputfunc = f;
}
```
所以，outputfunc 就是 net_tcpip_output，即 tcpip_output() 会调用函数 net_tcpip_output() 将 buf 发送出去。
# net_tcpip_output
```
static uint8_t net_tcpip_output(struct net_buf *buf, const uip_lladdr_t *lladdr)
{
	int res;

	if (!netdev.drv) {
		return 0;
	}

	if (lladdr) {
		linkaddr_copy(&ip_buf_ll_dest(buf),
			      (const linkaddr_t *)lladdr);
	} else {
		linkaddr_copy(&ip_buf_ll_dest(buf), &linkaddr_null);
	}

	if (ip_buf_len(buf) == 0) {
		return 0;
	}

	// 调用底层驱动程序，发送 buf ！！关于驱动程序如何发送数据，请参考后面的 net driver 相关章节。
	res = netdev.drv->send(buf);
	if (res < 0) {
		res = 0;
	}
	return (uint8_t)res;
}
```

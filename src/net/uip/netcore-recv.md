---
title: Zephys OS uIP 协议栈：netcore - 接收数据
date: 2016-10-13 22:39:19
categories: ["Zephyr OS"]
tags: [Zephyr]
---

这一节我们来学习 uIP 协议栈从网络中接收数据的流程。

- [net_receive](#net_receive)
    - [udp_packet_receive](#udp_packet_receive)
    - [simple_udp_register](#simple_udp_register)
- [net_rx_fiber](#net_rx_fiber)
    - [tcpip_input](#tcpip_input)
        - [tcpip_process](#tcpip_process)
        - [tcpip_uipcall](#tcpip_uipcall)
        - [simple_udp_process](#simple_udp_process)
    - [底层驱动的行为](#底层驱动的行为)

<!--more-->
# net_receive
应用程序如果需要接收来自其它设备的消息，需要调用函数 net_receive()。
```
struct net_buf *net_receive(struct net_context *context, int32_t timeout)
{
  // 获取该 context 所绑定的接收队列
	struct nano_fifo *rx_queue = net_context_get_queue(context);
	struct net_buf *buf;
	struct net_tuple *tuple;
	int ret = 0;
	uint16_t reserve = 0;

	tuple = net_context_get_tuple(context);
	if (!tuple) {
		return NULL;
	}

	switch (tuple->ip_proto) {
	case IPPROTO_UDP:
		if (!net_context_get_receiver_registered(context)) {
      // 如果该 context 还未注册 udp，则进行 udp 注册

			struct simple_udp_connection *udp = net_context_get_udp_connection(context);
			ret = simple_udp_register(udp, tuple->local_port,
#ifdef CONFIG_NETWORKING_WITH_IPV6
				(uip_ip6addr_t *)&tuple->remote_addr->in6_addr,
#else
				(uip_ip4addr_t *)&tuple->remote_addr->in_addr,
#endif
				tuple->remote_port,
				udp_packet_receive,
				context);
			if (!ret) {
				NET_DBG("UDP connection listener failed\n");
				ret = -ENOENT;
				break;
			}
		}
    // 设置标志为“已注册”
		net_context_set_receiver_registered(context);
		ret = 0;
		reserve = UIP_IPUDPH_LEN + UIP_LLH_LEN;
		break;
	case xxxxx:
    ......
		break;
	}

	if (ret) {
		return NULL;
	}

  // 从 context 绑定的 rx_queue 中获取来自其它网络设备的数据
	switch (timeout) {
	case TICKS_UNLIMITED:
	case TICKS_NONE:
		buf = net_buf_get_timeout(rx_queue, 0, timeout);
		break;
	default:
#ifdef CONFIG_NANO_TIMEOUTS
		buf = buf_wait_timeout(rx_queue, timeout);
#else /* CONFIG_NANO_TIMEOUTS */
		buf = net_buf_get_timeout(rx_queue, 0, TICKS_NONE);
#endif
		break;
	}

#ifdef CONFIG_NETWORKING_WITH_TCP
  ......
#endif

	if (buf && reserve) {
		ip_buf_appdatalen(buf) = ip_buf_len(buf) - reserve;
		ip_buf_appdata(buf) = &uip_buf(buf)[reserve];
	}

	return buf;
}
```
根据传入的参数 timeout 的值，该函数内部会做相应的处理：
- TICKS_NONE：无论是否获取到了数据，都立即返回。
- TICKS_UNLIMITED：只有获取到了数据才返回。如果获取不到数据，则一直陷入阻塞状态。
- 其它：在规定的时间内，如果获取到了数据，则返回。如果超过了规定的时间还未获取到数据，则返回超时的错误码。

整个函数的思路挺简单地，就是从 context 内部绑定的接收队列中取数据。如果能取出数据，那么就万事大吉；如果没有取出数据，也不关我们的事儿，让应用程序自己着急去吧。那么问题来了，我们只知道取数据，但是是谁让这个 buf 中放数据呢？

我们根据代码中的线索，一路追踪下去。在上面的函数内部，左看右看，上看下看，只有一个可疑之处：simple_udp_register。该函数的入参有一个回调函数，udp_packet_receive，我们先来看看它里面的内容。
## udp_packet_receive
```
static void udp_packet_receive(struct simple_udp_connection *c,
			       const uip_ipaddr_t *source_addr,
			       uint16_t source_port,
			       const uip_ipaddr_t *dest_addr,
			       uint16_t dest_port,
			       const uint8_t *data, uint16_t datalen,
			       void *user_data,
			       struct net_buf *buf)
{
	struct net_context *context = user_data;

	if (!context) {
		/* If the context is not there, then we must discard
		 * the buffer here, otherwise we have a buffer leak.
		 */
		ip_buf_unref(buf);
		return;
	}

	ip_buf_appdatalen(buf) = datalen;
	ip_buf_appdata(buf) = &uip_buf(buf)[UIP_IPUDPH_LEN + UIP_LLH_LEN];
	ip_buf_len(buf) = datalen + UIP_IPUDPH_LEN + UIP_LLH_LEN;

	nano_fifo_put(net_context_get_queue(context), buf);
}
```
在这个回调函数内部，先对 buf 进行了一些处理，然后通过 net_context_get_queue(context) 获取到该 buf 所在的 context 所绑定的 rx_queue，然后将该 buf 放到这个接收队列中。

虽然我们在这个回调函数中的确看到有往 context 的 rx_queue 中放数据，但是这个回调函数在什么时候会别调用呢？我们只能继续追踪 simple_udp_register 内部的代码。
## simple_udp_register
```
int simple_udp_register(struct simple_udp_connection *c,
                    uint16_t local_port,
                    uip_ipaddr_t *remote_addr,
                    uint16_t remote_port,
                    simple_udp_callback receive_callback,
                    void *user_data)
{

  init_simple_udp();

  c->local_port = local_port;
  c->remote_port = remote_port;
  if(remote_addr != NULL) {
    uip_ipaddr_copy(&c->remote_addr, remote_addr);
  }
  // 将回调函数放到 simple_udp_connection 这个结构体的内部了
  c->receive_callback = receive_callback;
  c->user_data = user_data;

  // 切换线程到 simple_udp_process
  PROCESS_CONTEXT_BEGIN(&simple_udp_process);
  c->udp_conn = udp_new(remote_addr, UIP_HTONS(remote_port), c);
  if(c->udp_conn != NULL) {
    udp_bind(c->udp_conn, UIP_HTONS(local_port));
  }
  PROCESS_CONTEXT_END();

  if(c->udp_conn == NULL) {
    return 0;
  }
  return 1;
}
```

我们看看 udp_new() 这个函数。它的第三个参数 appstate 就是 simple_udp_register() 内部传入的 c 变量，而该变量内部保存了我们设置的回调函数：
```
struct uip_udp_conn *udp_new(const uip_ipaddr_t *ripaddr, uint16_t port, void *appstate)
{
  struct uip_udp_conn *c;
  uip_udp_appstate_t *s;

  // 新建了一个 struct uip_udp_conn 类型的 c 变量
  c = uip_udp_new(ripaddr, port);
  if(c == NULL) {
    return NULL;
  }

  // 将指针 s 指向 c 变量的 appstate 成员。
  s = &c->appstate;
  // 将 c 变量的 appstate 成员的 p 成员指向 PROCESS_CURRENT。在上面，我们已经将线程
  // 切换到 simple_udp_process 了，所以就是 p 指向了线程 simple_udp_process
  s->p = PROCESS_CURRENT();
  // 将 c 变量的 appstate 成员的 state 成员指向上面传入的 appstate
  s->state = appstate;

  // 返回新建的 struct uip_udp_conn 类型的 c 变量
  return c;
}
```
这个函数返回的 c 变量的状态：
- c->appstate->p = simple_udp_process
- c->appstate->state->receive_callback 就是我们绑定的回调函数。

好复杂！！！

那么问题来了，然后呢？然后我们返回到 net_receive() 函数内部，然后，然后，就没有然后了，线索断了。

# net_rx_fiber
不要忘了，我们在 net_core 的初始化过程中，还创建了一个线程 net_rx_fiber。
```
static void net_rx_fiber(void)
{
	struct net_buf *buf;

	NET_DBG("Starting RX fiber (stack %zu bytes)\n",
		sizeof(rx_fiber_stack));

	while (1) {
    // 从 netdev 中绑定的 rx_queue 中获取从数据。如果获取不到，则陷入阻塞状态，直到
    // 有数据被放到该 rx_queue 中。
		buf = net_buf_get_timeout(&netdev.rx_queue, 0, TICKS_UNLIMITED);

    // 对该 buf  进行处理
		if (!tcpip_input(buf)) {
			ip_buf_unref(buf);
		}

	}
}
```
上面的函数很简单，从 netdev 绑定的 rx_queu 中获取数据，然后将数据交给 tcpip_input() 处理。此时我们又面临两个问题：
- 谁让 netdev 中的 rx_queue 中存放的数据呢？
- tcpip_input() 内部是如何处理的？

## tcpip_input
```
uint8_t tcpip_input(struct net_buf *buf)
{
  // 向 tcpip_process 线程投递了一个 PACKET_INPUT 事件
  process_post_synch(&tcpip_process, PACKET_INPUT, NULL, buf);
  ......
  return 1;
}
```
### tcpip_process
```
PROCESS_THREAD(tcpip_process, ev, data, buf, user_data)
{
  PROCESS_BEGIN();
  ......
  while(1) {
    PROCESS_YIELD();
    // 调用函数 eventhandler 处理投递进来的事件
    eventhandler(ev, data, buf);
  }

  PROCESS_END();
}
```

由于函数调用层级太深，我们就不将每个函数都罗列出来了，只简单地描述一下它们的调用关系:
```
  eventhandler()
      --->packet_input()
        --->uip_input()
          --->uip_process
            --->UIP_APPCALL
              --->tcpip_uipcall
```
### tcpip_uipcall
```
void tcpip_uipcall(struct net_buf *buf)
{
  struct tcpip_uipstate *ts;

#if UIP_UDP
  if(uip_conn(buf) != NULL) {
    ts = &uip_conn(buf)->appstate;
  } else {
    // 我们的代码会走到这里
    // 这里的 ts，就是我们在注册 udp 时的 c->appstate
    ts = &uip_udp_conn(buf)->appstate;
  }
#else /* UIP_UDP */
  ts = &uip_conn(buf)->appstate;
#endif /* UIP_UDP */

  ......

  if(ts->p != NULL) {
    // ts-p 就是我们在注册 udp 时的 c->appstae->p，即 simple_udp_process
    // 所以这里向线程 simple_udp_process 投递了一个 tcpip_event 事件
    process_post_synch(ts->p, tcpip_event, ts->state, buf);
  }
}
```
### simple_udp_process
```
PROCESS_THREAD(simple_udp_process, ev, data, buf, user_data)
{
  struct simple_udp_connection *c;
  PROCESS_BEGIN();

  while(1) {
    PROCESS_WAIT_EVENT();
    if(ev == tcpip_event) {
      c = (struct simple_udp_connection *)data;
      if(c != NULL) {
        if(uip_newdata(buf)) {

          if(c->receive_callback != NULL) {
            PROCESS_CONTEXT_BEGIN(c->client_process);
            // 调用我们注册的回调函数
            c->receive_callback(c,
                                &(UIP_IP_BUF(buf)->srcipaddr),
                                UIP_HTONS(UIP_IP_BUF(buf)->srcport),
                                &(UIP_IP_BUF(buf)->destipaddr),
                                UIP_HTONS(UIP_IP_BUF(buf)->destport),
                                uip_appdata(buf), uip_datalen(buf),
                                c->user_data, buf);
            PROCESS_CONTEXT_END();
          }
        }
      }
    }

  }

  PROCESS_END();
}
```
## 底层驱动的行为
我们还遗留了一个问题，即是谁向 netdev 的 rx_queue 中存放数据的呢。暂时不深入分析了，简单地总结了一下它们的调用关系。

```
fifop_int_handler（当 cc2520 接收到信号时，会触发这个中断，这个中断内部会释放一个信号量 rx_lock）
  ---> cc2520_rx（拿取到信号量 rx_lock 后，将数据读取到一个 buf 中）
    --->net_driver_15_4_recv_from_hw（将读取到的 buf 放到 net_driver 的 rx_queue 中）
      --->net_rx_15_4_fiber（从 net_driver 的 rx_queue 中取出数据，然后调用 NETSTACK_RDC）
        --->[struct rdc_driver sicslowmac_driver] NETSTACK_RDC.input
          --->[struct mac_driver csma_driver] NETSTACK_MAC.input
            -->[struct llsec_driver nullsec_driver] NETSTACK_LLSEC.input
              --->[struct fragmentation sicslowpan_fragment] NETSTACK_FRAGMENT.reassemble
                --->net_driver_15_4_recv
                  --->[struct compression sicslowpan_compression] NETSTACK_COMPRESS.uncompress
                  --->net_recv （将buf中的数据放到 netdev 的 rx_queue 中）
```
# 总结
应用程序在接收数据时，总共涉及到多个 rx_queue：
- net_driver 的 rx_queue：底层驱动将从信道中接收到的帧放到这个队列中，经过底层驱动的解封装后，再被放到 netdev 的接收队列中。
- netdev 的 rx_queue：取出这个队列中的数据，解析其上层协议头部，然后放入到 context 的接收队列中。
- contex 的 rx_queue：应用程序从这个接收队列中取数据。如果取得数据，则直接返回。如果取不到数据，则陷入阻塞，直到取到数据。

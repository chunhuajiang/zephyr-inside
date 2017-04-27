# 由一个示例入手

Zephyr 提供了一套与 socket（套接字） 非常类似的接口，叫做 context（上下文），这些接口在头文件`include/net/net_context.h`中定义。

## 与 socket 的对应关系

socket 与 context 的一一对应关系如下：

功能 | socket  | context 
---- | ------  | ---    
创建 | socket  | net_context_get 
关闭 | close   | net_context_put
绑定 | bind    | net_context_bind
连接 | connect | net_context_connect
接收连接请求 | accept | net_context_accept
监听 | listen | net_context_listen
发送 | send   | net_context_send
发送 | sendto | net_context_sendto
接收 | recv    | net_context_recv

## 示例代码分析

此外，Zephyr 还提供了一个简单的服务器示例代码，来说明如何使用这些 context 接口。该服务器程序会监听发送过来的 UDP 连接并将接收到的数据再送回去。

服务器示例代码位于：[https://gerrit.zephyrproject.org/r/gitweb?p=zephyr.git;a=blob;f=doc/subsystems/networking/connectivity-example-app.c#l37](https://gerrit.zephyrproject.org/r/gitweb?p=zephyr.git;a=blob;f=doc/subsystems/networking/connectivity-example-app.c#l37)

下面简单分析下该示例代码。

### main 函数

```
#define SYS_LOG_DOMAIN "example-app"
#define SYS_LOG_LEVEL SYS_LOG_LEVEL_DEBUG
#define NET_DEBUG 1

#include <zephyr.h>

#include <net/nbuf.h>
#include <net/net_core.h>
#include <net/net_context.h>

#define MY_IP6ADDR { { { 0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, \
			 0, 0, 0, 0, 0, 0, 0, 0x1 } } }
#define MY_PORT 4242

struct in6_addr in6addr_my = MY_IP6ADDR;
struct sockaddr_in6 my_addr6 = { 0 };
struct net_context *context;
int ret;

void main(void)
{
	NET_INFO("Run sample application");

	init_app();

	create_context();

	bind_address();

	receive_data();

	nano_sem_take(&quit_lock, TICKS_UNLIMITED);

	close_context();

	NET_INFO("Stopping sample application");
}
```

在 main 函数开始时，进行了与应用程序相关的初始化。

### 应用程序相关的初始化
```
struct nano_sem quit_lock;

static inline void quit(void)
{
	nano_sem_give(&quit_lock);
}

static inline void init_app(void)
{
	nano_sem_init(&quit_lock);

	/* Add our address to the network interface */
	net_if_ipv6_addr_add(net_if_get_default(), &in6addr_my,
			     NET_ADDR_MANUAL, 0);
}

```

在 init_app 里面，它先初始化了一个信号量（该信号量的作用在后面说明），然后在网络接口上设置本机的 IPv6 地址。这里有一个非常重要的概念——接口（interface），它与 linux 下的接口是等同概念，我们将在后续详细分析。

### 创建 context

```
static int create_context(void)
{
	ret = net_context_get(AF_INET6, SOCK_DGRAM, IPPROTO_UDP, &context);
	if (!ret) {
		NET_ERR("Cannot get context (%d)", ret);
		return ret;
	}

	return 0;
}
```

初始化后，应用程序所做的第一件事儿是调用 net_context_get() 函数创建一个 context，即类似于创建一个 socket。

### 绑定 context

```
static int bind_address(void)
{
	net_ipaddr_copy(&my_addr6.sin6_addr, &in6addr_my);
	my_addr6.sin6_family = AF_INET6;
	my_addr6.sin6_port = htons(MY_PORT);

	ret = net_context_bind(context, (struct sockaddr *)&my_addr6);
	if (ret < 0) {
		NET_ERR("Cannot bind IPv6 UDP port %d (%d)",
			ntohs(my_addr6.sin6_port), ret);
		return ret;
	}

	return 0;
}
```

然后绑定本机地址到上面所创建的 context 上。

### 接收数据

```
static int receive_data(void)
{
	ret = net_context_recv(context, udp_received, 0, NULL);
	if (ret < 0) {
		NET_ERR("Cannot receive IPv6 UDP packets");

		quit();

		return ret;
	}

	return 0;
}
```

是一个回调函数，即当系统接收到数据后，会自动调用该函数进行应用程序相关的处理。
然后开始接听数据。需要注意的是，该函数 net_context_recv() 是一个异步函数，它的第二个参数 udp_received 

我们继续看该函数 udp_received() 。
```
static void udp_received(struct net_context *context,
			 struct net_buf *buf,
			 int status,
			 void *user_data)
{
	struct net_buf *reply_buf;
	struct sockaddr dst_addr;
	sa_family_t family = net_nbuf_family(buf);
	static char dbg[MAX_DBG_PRINT + 1];
	int ret;

	snprintf(dbg, MAX_DBG_PRINT, "UDP IPv%c",
		 family == AF_INET6 ? '6' : '4');

	// 从buffer中获取发送方的IP地址
	set_dst_addr(family, buf, &dst_addr);
	
	// 从buffer中获取发送方所发送的数据，并根据该数据准备要回送
	// 给发送方的buffer（该buffer与接收到的buffer不是同一个buffer）
	reply_buf = udp_recv(dbg, context, buf);
	
	// 接收到的发送方的数据已在上面使用完毕，释放该buffer
	net_nbuf_unref(buf);

	// 再将准备回送的buffer中的数据发送出去
	ret = net_context_sendto(reply_buf, &dst_addr, udp_sent, 0,
				 UINT_TO_POINTER(net_buf_frags_len(reply_buf)),
				 user_data);
	if (ret < 0) {
		NET_ERR("Cannot send data to peer (%d)", ret);

		net_nbuf_unref(reply_buf);

		quit();
	}
}
```
函数第第二个参数 struct net_buf *buf 指向该 context 所接收到接收到的数据所存放的 buffer。具体处理过程详见上面添加的注释。

### 获取信号量

我们前面说函数 receive_data() 是异步的，所以该函数执行完后会立即执行下一条语句，即:
```
nano_sem_take(&quit_lock, TICKS_UNLIMITED);
```
来获取信号量，由于当前无法获取到信号量，所以陷入阻塞，然后系统会进行上下文切换，去执行系统中其它线程（例如协议栈中所创建的线程）。在某一个时候，协议栈中的线程通过网卡接收到数据后，它会调用我们在 net_context_recv() 时传入的回调函数 udp_received()，而在该函数内部则会释放信号量。然后，main线程会在某个时候被切换回来继续执行，此时获取信号量就成功了，然后继续执行后面的代码。

### 关闭 context
```
static int close_context(void)
{
	ret = net_context_put(context);
	if (ret < 0) {
		NET_ERR("Cannot close IPv6 UDP context");
		return ret;
	}

	return 0;
}
```
关闭 context。

## 总结

* 使用 context 进行网络编程与使用 socket 进行网络编程几乎完全一致。
* 执行函数 udp_received() 时的上下文并非是 main 线程。
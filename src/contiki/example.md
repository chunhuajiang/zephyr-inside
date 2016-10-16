我们现在结合一个例子，来综合分析一下前面所学的内容。

在这个例子里，我们创建两个线程，一个线程叫 hello_process，另一个线程叫 world_process。在 hello_process 线程里，创建了一个定时器，该定时器的周期为 1 秒，即事件定时器线程每隔 1 秒会向 hello_process 线程投递一个定时器事件 PROCESS_EVENT_TIMER，所以 hello_process 每 1 秒会被调度一次。当 hello_process 线程被调度后，它会向 world_process 线程投递一个事件，然后 world_process 线程会被执行一遍。
# 头部
```
#include "contiki.h"
#include <stdio.h>

static process_event_t my_event;

PROCESS(hello_process, "Hello process");
PROCESS(world_process, "World process");
```

# hello_process 线程
```
PROCESS_THREAD(hello_process, ev, data)
{  
  PROCESS_BEGIN();

  static struct etimer timer;

  // 定时器每秒触发一次
  etimer_set(&timer, CLOCK_CONF_SECOND);

  printf("hello process started\n");

  // 分配一个新的事件(事件编号)
  my_event = process_alloc_event();

  while(1)
  {
    // 等待定时器事件到来
    PROCESS_WAIT_EVENT_UNTIL(ev == PROCESS_EVENT_TIMER);

    printf("Hello\n");

    // 向 world_process 线程投递一个我们分配的事件
    process_post_synch(&world_process, my_event, NULL);

    // 重置定时器
    etimer_reset(&timer);
  }

  PROCESS_END();
}
```
# world_process 线程
```
PROCESS_THREAD(world_process, ev, data)
{
  PROCESS_BEGIN();
  printf("world process started!\n");
  while(1)
  {
    PROCESS_WAIT_EVENT_UNTIL(ev == my_event);
    printf("world\n");
  }
  PROCESS_END();
}
```
# 主函数
下面我们来看看主函数里的内容应该如何写（忽略一些硬件相关的细节）。
```
int main()
{
  process_init();
  process_start(&etimer_process， NULL);
  process_start(&hello_process, NULL);
  process_start(&world_process, NULL);

  while(1)
  {
    uint8_t r;
    do {
      r = process_run();
    } while(r > 0)
  }
}
```
# 程序输出
理论上，程序的输出结果应该是：
```
hello process started!
world process started!
hello
world
hello
world
......
```
# 分析
从主函数入手，我们分析一下整个代码。
- 初始化线程环境 process_init：process_init() 内部会初始化全局的线程链表 process_list。


- 启动 etimer_process:在《线程调度》一节中，我们已经知道，启动一个线程时，会先将该线程加入线程链表 process_list 中，然后执行一遍该线程的执行实体。我们看看 etimer_process 这个线程在此时做了什么：

```
PROCESS_THREAD(etimer_process, ev, data)
{
  struct etimer *t, *u;

  PROCESS_BEGIN();

  // 初始化定时器链表，此时该链表为空
  timerlist = NULL;

  while(1) {
    // PROCESS_YIELD() 会立即退出本线程，当 etimer_process 被再次调度时，
    // 会从此处继续执行，具体原因请参考《线程切换》一节。
    PROCESS_YIELD();
    ......
```
- 启动 hello_process:先将 hello_process 加入到线程链表 process_list 中，然后执行该线程。我们看看 hello_process 这线程在此时做了什么：

```
PROCESS_THREAD(hello_process, ev, data)
{  
  PROCESS_BEGIN();
  static struct etimer timer;

  // 设置定时器。etimer_set 内部会将 hello_process 这个线程加入到
  // 定时器的链表 timelist 中。
  etimer_set(&timer, CLOCK_CONF_SECOND);
  // 向串口输出“hello process started”
  printf("hello process started\n");

  // 分配一个新的事件(事件编号)
  my_event = process_alloc_event();

  while(1)
  {
    // PROCESS_WAIT_EVENT_UNTIL() 会立即退出本线程，当 hello_process 被再次调度时，
    // 且投递给该线程的事件为定时器事件时，本线程才会继续执行，具体原因请参考《线程切换》
    // 一节。
    PROCESS_WAIT_EVENT_UNTIL(ev == PROCESS_EVENT_TIMER);
```

- 启动 world_process:先将 world_process 加入到线程链表 process_list 中，然后执行该线程。我们看看 hello_process 这线程在此时做了什么：

```
PROCESS_THREAD(world_process, ev, data)
{
  PROCESS_BEGIN();
  // 向串口输出“world process started!”
  printf("world process started!\n");
  while(1)
  {
    // PROCESS_WAIT_EVENT_UNTIL() 会立即退出本线程，当 world_process 被再次调度时，
    // 且投递给该线程的事件为 my_event 时，本线程才会继续执行，具体原因请参考《线程切换》
    // 一节。
    PROCESS_WAIT_EVENT_UNTIL(ev == my_event);
```
- 调度器 process_run()

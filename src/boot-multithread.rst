.. boot-multithread:

.. highlight:: c
   :linenothreshold: 1

系统启动 - 多线程阶段
============================

经过前面两个阶段后，我们终于可以舒坦地看 C 代码了。

本节我们主要理一理系统是怎么运行到 main 函数去的。

.. contents::
   :depth: 3
   :local:
   :backlinks: top

_Cstart
****************************

    FUNC_NORETURN void _Cstart(void)
    {
    #ifdef CONFIG_ARCH_HAS_CUSTOM_SWAP_TO_MAIN
    	...
    #else
    	/* floating point is NOT used during kernel init */
    	char __stack dummy_stack[_K_THREAD_NO_FLOAT_SIZEOF];
    	void *dummy_thread = dummy_stack;
    #endif
    
    	/*
    	 * Initialize kernel data structures. This step includes
    	 * initializing the interrupt subsystem, which must be performed
    	 * before the hardware initialization phase.
    	 */
    
    	prepare_multithreading(dummy_thread);
    
    	/* Deprecated */
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRIMARY);
    
    	/* perform basic hardware initialization */
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRE_KERNEL_1);
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRE_KERNEL_2);
    
    	/* initialize stack canaries */
    
    	STACK_CANARY_INIT();
    
    	/* display boot banner */
    
    	PRINT_BOOT_BANNER();
    
    	switch_to_main_thread();
    
    	/*
    	 * Compiler can't tell that the above routines won't return and issues
    	 * a warning unless we explicitly tell it that control never gets this
    	 * far.
    	 */
    
    	CODE_UNREACHABLE;
    }
    
	
上面这段代码，我们主要关注四个地方：

* dummy_thread：定义了一个“虚拟”线程
* prepare_multithreading：准备多线程环境
* _sys_device_do_config_level：初始化各级设备
* switch_to_main_thread：切换到 main 线程

虚拟线程
****************************

下面这两句话定义了一个线程？ ::

    char __stack dummy_stack[_K_THREAD_NO_FLOAT_SIZEOF];
    void *dummy_thread = dummy_stack;

是的！站在狭义的角度上讲，它定义了一个线程。初次接触，肯定会很不能理解，那么上面这这段代码做了上面？

* 定义了一个数组，即一段内存空间。

其中，__stack 是一个修饰符，表示这个数组是按照栈的要求对齐的(通常是 4 字节对齐)。_K_THREAD_NO_FLOAT_SIZEOF 表示这个数组的大小，它其实是结构体 struct k_thread 所占内存空间的大小(如果配置了对浮点的支持，不包括浮点结构的大小)。struct k_thread 是用于描述线程控制信息的结构体。

请注意到前面的修饰词，这是个“虚拟”的线程，那么真实的线程是怎么样的呢？真实线程也是一个数组，不同之处在于该数组除了 struct k_thread 的大小外，还包括这个线程可用栈空间的大小。我们这里只是初步了解下概念，关于线程的详细信息请参考后续的线程相关的章节。

准备多线程环境
****************************

    static void prepare_multithreading(struct k_thread *dummy_thread)
    {
    #ifdef CONFIG_ARCH_HAS_CUSTOM_SWAP_TO_MAIN
    	...
    #else
    	_current = dummy_thread;
    	dummy_thread->base.flags = K_ESSENTIAL;
    #endif
    
		// 将所有的中断优先级设为默认优先级
    	_IntLibInit();
    
    	// 初始化内核大总管中的就绪队列
		// 关于内核大总管，请参考《Zephyr OS 内核篇：内核大总管 _kernel》
    	for (int ii = 0; ii < K_NUM_PRIORITIES; ii++) {
    		sys_dlist_init(&_ready_q.q[ii]);
    	}
    
		// 将 main 线程添加到内核大总管维护的就绪队列中去，
		// 且让它作为下次线程切换时最优先调度的线程
    	_ready_q.cache = _main_thread;
    
		// 创建了两个线程，一个 main 线程，一个 idel 线程
    	_new_thread(_main_stack, MAIN_STACK_SIZE,
    		    _main, NULL, NULL, NULL,
    		    CONFIG_MAIN_THREAD_PRIORITY, K_ESSENTIAL);
    	_mark_thread_as_started(_main_thread);
    	_add_thread_to_ready_q(_main_thread);
    
    #ifdef CONFIG_MULTITHREADING
    	_new_thread(_idle_stack, IDLE_STACK_SIZE,
    		    idle, NULL, NULL, NULL,
    		    K_LOWEST_THREAD_PRIO, K_ESSENTIAL);
    	_mark_thread_as_started(_idle_thread);
    	_add_thread_to_ready_q(_idle_thread);
    #endif
    
		// 初始化超时服务
    	initialize_timeouts();
		// 执行一些架构相关的初始化
    	nanoArchInit();
    }

上面的代码主要做了两件事儿，其一创建了 main 和 idel 两个线程，其二是做了一些相关初始化。

我们当前只关注一点，即创建线程时会指定线程的入口函数。对于 main 线程，它的入口函数是 _main()。
	
设备的初始化
****************************

相关代码： ::

    	/* Deprecated */
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRIMARY);
    
    	/* perform basic hardware initialization */
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRE_KERNEL_1);
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_PRE_KERNEL_2);

Zephyr 支持多种设备，且这些设备是分级的：

* PRE_KERNEL_1
* PRE_KERNEL_2
* POST_KERNEL
* APPLICATION

各个设备在使用前都需要进行某些初始化操作。这个阶段会先初始化 PRE_KERNEL_1 和 PRE_KERNEL_2 这两个等级的设备。PRIMARY 是 v1.6.0 前的代码所使用的设备等级，现在已经不用了。至于 _sys_device_do_config_level() 是如何对设备进行初始化的，请参考《Zephyr OS 驱动篇：设备驱动和设备模型》。


切换到 main 线程
****************************

函数 switch_to_main_thread 用于将上下文切换到 main 线程： ::

    static void switch_to_main_thread(void)
    {
    #ifdef CONFIG_ARCH_HAS_CUSTOM_SWAP_TO_MAIN
    	...
    #else
    	_Swap(irq_lock());
    #endif
    }

它里面其实就一句话，先锁定中断，再调用函数 _Swap() 进行切换。其实 _Swap() 的本质是在汇编中定义的，我们会在后面的章节中单独讲解。	
	
在前面准备多线程环境的过程中，_ready_q.cache = _main_thread 会将 main 线程作为即将被切换的线程，因此当此时执行 _Swap() 时就会切换到 main 线程，即执行该线程的入口函数 _main()： ::

    static void _main(void *unused1, void *unused2, void *unused3)
    {
    	ARG_UNUSED(unused1);
    	ARG_UNUSED(unused2);
    	ARG_UNUSED(unused3);
    
		// 初始化 POST_KERNEL 级别的设备
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_POST_KERNEL);
    
    	/* 下面这三个初始化是为了兼容v1.6.0前的代码 */
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_SECONDARY);
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_NANOKERNEL);
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_MICROKERNEL);
    
    	// 初始化 APPLICATION 级别的设备
    	_sys_device_do_config_level(_SYS_INIT_LEVEL_APPLICATION);
    
    #ifdef CONFIG_CPLUSPLUS
		// 初始化 C++ 执行环境
    #endif
    
    	_init_static_threads();
    
    #ifdef CONFIG_BOOT_TIME_MEASUREMENT
		// 记录启动时间戳的，不用关心
    #endif
    
    	extern void main(void);
    #if defined(MDEF_MAIN_THREAD_PRIORITY) && (MDEF_MAIN_THREAD_PRIORITY != CONFIG_MAIN_THREAD_PRIORITY)
		// 设置 main 线程的优先级
    	k_thread_priority_set(_main_thread, MDEF_MAIN_THREAD_PRIORITY);
    #endif
		// 进入 main 函数去执行！！！
    	main();
    
    	/* Terminate thread normally since it has no more work to do */
    	_main_thread->base.flags &= ~K_ESSENTIAL;
    }
	
总结
****************************

本节我们故意略过了很多细节，这些细节在我们后面的学习过程中会慢慢讲解。
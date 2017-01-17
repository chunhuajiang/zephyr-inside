.. boot-prep-c:

.. highlight:: c
   :linenothreshold: 1

系统启动 - C 准备阶段
============================

在上一节的最后，代码已经跳转到 _PrepC()： ::

  void _PrepC(void)
  {
  	  relocate_vector_table();
  	  enable_floating_point();
  	  _bss_zero();
  	  _data_copy();
  	  _Cstart();
  	  CODE_UNREACHABLE;
  }


咋一看，这都是 C 代码了，那么我们可以任意使用 C 代码了吗？答案是 NO！这只是表象，此时的 C 代码还受到限制，例如不能使用全局变量、静态变量等。因此，这部分的 C 代码只是为了能够真正畅快地运行 C 代码做准备。

.. contents::
   :depth: 3
   :local:
   :backlinks: top

两种启动模式
****************************

在 Zephyr OS 中，系统有两种启动模式，在不同的启动模式下需要做的准备工作不一样。这两种启动模式是：

* XIP 模式
* 非 XIP 模式

XIP 即 eXecute In Place，中文名为“就地执行”。在 XIP 模式下，CPU 可以像直接读内存一样地直接从 (Nor) Flash 上面读取代码；在非 XIP 模式下，必须由硬件先将代码从 Flash 上面搬移到 RAM 上面后，CPU 才能直接访问这些数据。

是否支持 XIP 模式与 SoC 的设计有关。

关于 XIP 的更多信息请参考 `eXecute In Place <https://en.wikipedia.org/wiki/Execute_in_place>`_ 。

重定位向量表
****************************

函数 relocate_vector_table() 用于重定位向量表： ::

  #ifdef CONFIG_XIP
  static inline void relocate_vector_table(void) { /* do nothing */ }
  #else
  static inline void relocate_vector_table(void)
  {
     /* vector table is already in SRAM, just point to it */
     _scs_relocate_vector_table((void *)CONFIG_SRAM_BASE_ADDRESS);
  }
  #endif

对于 Cortex-M3，向量表默认位于地址 0x0 处。

对于 XIP 模式，SoC 通常会将 Flash 映射到地址 0x0 处，因此无需再对向量表进行重定位。

对于非 XIP 模式，代码已经被已经搬移到 SRAM 中的，因此我们需要将向量表重定位寄存器赋值为 SRAM 的起始地址即可。

如何知道非 XIP 模式下的向量表是位于 SRAM 中的？这从链接脚本中可以看到： ::

    #ifdef CONFIG_XIP
      #define ROMABLE_REGION FLASH
      #define RAMABLE_REGION SRAM
    #else
      #define ROMABLE_REGION SRAM
      #define RAMABLE_REGION SRAM
    #endif
    
    .....
    
    MEMORY
        {
        FLASH                 (rx) : ORIGIN = ROM_ADDR, LENGTH = ROM_SIZE
        SRAM                  (wx) : ORIGIN = RAM_ADDR, LENGTH = RAM_SIZE
        SYSTEM_CONTROL_SPACE  (wx) : ORIGIN = 0xE000E000,  LENGTH = 4K
        SYSTEM_CONTROL_PERIPH (wx) : ORIGIN = 0x400FE000,  LENGTH = 4K
        }
    
    SECTIONS
        {
        GROUP_START(ROMABLE_REGION)
    
    	_image_rom_start = CONFIG_FLASH_BASE_ADDRESS;
    
        SECTION_PROLOGUE(_TEXT_SECTION_NAME,,)
    	{
    	KEEP(*(.exc_vector_table))
    	KEEP(*(".exc_vector_table.*"))
    
    	KEEP(*(.irq_vector_table))
    	KEEP(*(".irq_vector_table.*"))
        
        ...
    	} GROUP_LINK_IN(ROMABLE_REGION)

我们可以看到，向量表会被链接到 ROMABLE_REGION 中，而非 XIP 模式下的 ROMABLE_REGION 即 SRAM。

非 XIP 模式下如果不进行重定位会怎样？当发生异常或中断时，CPU 会找到到一个错误的异常/中断入口地址，然后就跑飞了。

.. Hint::
  
   疑问：我们的代码是如何从 FLASH 上面跑到 SRAM 上面的？复位向量的入口地址是如何找到的？

使能浮点功能
****************************

这部分功能是可选的，略。

清 BSS 段
****************************

BSS 段是干什么的？首先，它是一段内存空间；其次，程序中的静态变量和全局变量就是存放于这个段的。系统上电后，内存中的值是不可预料的，因此 BSS 段中的值也是不可预料的。对于 C 语言，我们都知道，全局变量和静态变量的默认值是 0，要使这些变量在不初始化时的值为 0，我们必须将 BSS 段中的每个地址的值都设为 0。

BSS 段的初始化非常简单： ::

    void _bss_zero(void)
    {
    	memset(&__bss_start, 0, ((uint32_t) &__bss_end - (uint32_t) &__bss_start));
    }

该函数直接用 memset 函数将 BSS 段中的内存设为 0。__bss_start 和 __bss_end 都是在链接脚本中定义的符号，它们分别表示 BSS 段的起始地址和结束地址。

数据拷贝
****************************

函数 _data_copy 用于数据拷贝： ::

    #ifdef CONFIG_XIP
    void _data_copy(void)
    {
    	memcpy(&__data_ram_start, &__data_rom_start, ((uint32_t) &__data_ram_end - (uint32_t) &__data_ram_start));
    }
    #else
    static inline void _data_copy(void)
    {
    	/* Do nothing */
    }
    #endif

对于 XIP 模式，我们的代码是位于 Flash 上面的，CPU 虽然可以直接像读内存一样地读取 Flash 上面的代码，但是速度却比 RAM 满多了。

对于非 XIP 模式，代码已经位于 SRAM 上面了，因此无需任何操作。

总结
****************************

之后，系统就可以完全自由地使用 C 代码了，我们总结一下系统上电后做了哪些必要的事儿：

* 查找向量表，并跳转到复位向量的入口处开始执行；
* 屏蔽中断。由于我们的环境还未初始化好，先屏蔽中断；
* 关闭看门狗。在初始化阶段，我们可能无法按时喂狗，因此如果看门狗在开机后默认被使能了，则先关闭看门狗；
* 初始化栈指针。在函数调用时，参数的传递、返回值的传递都会有压栈、出栈操作；
* 重定位向量表；
* 清 BSS 段；
* 将代码从 Flash 拷贝到内存(XIP 模式下)；




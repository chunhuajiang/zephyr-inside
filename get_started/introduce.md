# Zephyr 简介

Zephyr 是由 Linux 基金会于 2016 年 2 月发布的一个用于物联网的开源操作系统。Linux 基金会希望借助于 Zephyr 来统一联网物联网领域的操作系统。

## Zephyr 的优势

市面上已有不少的 RTOS，Linux 基金为啥会还会推出 Zephyr？先看看 Zephyr 具有哪些。

### 轻量级

由于 IoT 领域需要部署大量的联网设备节点，因此每个设备的成本必须得到控制。控制成本第一个有效方法是降低昂贵组件的标准，例如使用 RAM 更低、ROM 更低的芯片。Zephyr 就是专为这样的芯片而生的，它可运行在只有 8 Kb 内存的 MCU 之上，甚至能在只有 2 Kb 内存的 MCU 上演示 Hello World。

### 模块化

降低成本的另一个方式是按需裁剪硬件。物联网设备一般都是专用设备，因此在面对某个特定市场时只需要特定的硬件。 Zephyr 借鉴了 Linux 的 Kconfig 配置系统，您可以根据硬件设备对它进行直观的配置、裁剪。

### 多架构

Zephyr 没有任何门户之见，在被设计时就支持多架构，包括 x86、arm、nios2、riscv32、xtensa 和 arc。到目前为止，Zephyr 已支持非常多的开发板：

```
zephyr@ubuntu:~/share/zephyr$ tree boards/ -L 2 -d
boards/
├── arc
│   ├── arduino_101_sss
│   ├── em_starterkit
│   ├── panther_ss
│   └── quark_se_c1000_ss_devboard
├── arm
│   ├── 96b_carbon
│   ├── 96b_nitrogen
│   ├── arduino_101_ble
│   ├── arduino_due
│   ├── bbc_microbit
│   ├── cc3200_launchxl
│   ├── curie_ble
│   ├── frdm_k64f
│   ├── frdm_kw41z
│   ├── hexiwear_k64
│   ├── mps2_an385
│   ├── nrf51_blenano
│   ├── nrf51_pca10028
│   ├── nrf52840_pca10056
│   ├── nrf52_blenano2
│   ├── nrf52_pca10040
│   ├── nucleo_f103rb
│   ├── nucleo_f334r8
│   ├── nucleo_f401re
│   ├── nucleo_f411re
│   ├── nucleo_l476rg
│   ├── olimexino_stm32
│   ├── qemu_cortex_m3
│   ├── quark_se_c1000_ble
│   ├── sam_e70_xplained
│   ├── stm3210c_eval
│   ├── stm32373c_eval
│   ├── stm32_mini_a15
│   └── v2m_beetle
├── nios2
│   ├── altera_max10
│   └── qemu_nios2
├── riscv32
│   ├── qemu_riscv32
│   └── zedboard_pulpino
├── x86
│   ├── arduino_101
│   ├── galileo
│   ├── minnowboard
│   ├── panther
│   ├── qemu_x86
│   ├── quark_d2000_crb
│   ├── quark_se_c1000_devboard
│   └── tinytile
└── xtensa
    └── xt-sim
```


### 可移植性强

正如上面所看到的那样，Zephyr 现在已经支持非常多的开发板，且能比较容易地移植到其它开发板上。为啥移植性这么强？因为 Zephyr 在被设计时就考虑了可移植性，用户只需要添加少量与开发板相关的代码就能跑起来了。

### 完善的物联网协议

物联网一直在发展，存在的协议也多种多样，而且将来肯定还会有新的协议诞生，我们很难说哪个协议最终会脱颖而出，因为它们各自有自己的应用领域。因此，Zephyr 会尽可能多地包括这些协议。来看看 Zephyr 支持（以及今后会支持）哪些物联网协议：

<img src="./introd.png" align=center>

Zephyr 包括这么多协议会不会太臃肿？这不是与它所说的轻量级自相矛盾吗？答案是不会！我们前面已经说了，Zephyr 是高度可配置的，应用开发者可以根据自己项目的需要，只把相关的功能编译到镜像文件中，从而避免臃肿。

### 丰富的设备驱动

Zephyr 同样还支持丰富的设备驱动程序：

```
zephyr@ubuntu:~/share/zephyr$ tree drivers/ -L 1 -d
drivers/
├── adc
├── aio
├── bluetooth
├── clock_control
├── console
├── counter
├── crypto
├── dma
├── ethernet
├── flash
├── gpio
├── grove
├── i2c
├── ieee802154
├── interrupt_controller
├── ipm
├── pci
├── pinmux
├── pwm
├── random
├── rtc
├── sensor
├── serial
├── shared_irq
├── slip
├── spi
├── timer
├── usb
└── watchdog
```

### 活跃的社区支持

Zephyr 的社区非常活跃，从发布到现在短短一年时间内，Zephyr 的代码提交数量已经超过了一万三千次，这 绝对是一个惊人的数字，远远超越了其它类似的 RTOS，例如 mbed os、lite os、riot、contiki 等。

## Zephyr 的劣势

同样地，Zephyr 也有它的劣势，即学习门槛高。


首先，尽管 Zephyr 支持 Windows、Linux 和 Mac 三大操作系统，但是对 Windows 的支持是非常弱的，如果要在 Windows 上学习、开发 Zephyr，必然会走进很多坑，而 Mac 只有少数土豪拥有，所以 Linux 是最佳的开发环境。但是，很多嵌入式开发人员都是在 Windows 上进行开发的，很少甚至没有使用 Linux，因此对于这一类同胞来说，Linux 就是它们的第一道坎，只有翻过了这道坎，才能继续学习 Zephyr。

其次，尽管有 gdb，但是 Zephyr 没有提供更加直观的图形化开发、调试工具，这也增加了一定的门槛。

当然，这里所说的劣势，在资深开发人员眼中就完全忽略不计了。

## 对 Zephyr 的期待

下面这个视频是 Zephyr 社区工程师对 Zephyr 的评价。

<center>
<iframe height=400 width=610 src='http://player.youku.com/embed/XMjYxNDU0Nzk2OA==' frameborder=0 'allowfullscreen'></iframe>
</center>

正如视频中 Linux 基金会的执行总监 Jim Zemlin 所说，在现在的数百个实时操作系统中，他们选择了 Zephyr 进行投资，因为 Zephyr  值得他们信赖，它拥有庞大的生态系统，一个健康的、拥有未来的且自身可持续发展的生态系统。Zephyr 尽管处于发展初期，但可以说它是与 Linux 具有同等意义的代码库，是真正会促进 IoT 繁荣发展、为社会带来巨大价值的强大系统。
 
这仿佛是我们学习者的一注强心剂，让我们继续有动力学习下去！
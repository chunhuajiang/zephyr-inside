# 开发环境 - Ubuntu

Zephyr 的文档已经比较详细地说明了如何搭建开发环境，这里简略写下步骤。

## 安装依赖

```
$ sudo apt-get install git make gcc g++ python3-ply ncurses-dev python-yaml python2 dfu-util
```

## 安装 SDK

### 下载和安装
Zephyr 当前最新的 SDK 版本为 0.9，可以直接用命令安装：
```
$ wget https://nexus.zephyrproject.org/content/repositories/releases/org/zephyrproject/zephyr-sdk/0.9/zephyr-sdk-0.9-setup.run
$ sudo chmod +x zephyr-sdk-0.9-setup.run
$ sudo ./zephyr-sdk-0.9-setup.run
```
推荐使用默认的安装路径，即`/opt/zephyr-sdk`。

有很多朋友反映 SDK 下载速度奇慢无比，因此我将其上传到百度云了 —— [链接](http://96boards.net/forum.php?mod=viewthread&tid=54&extra=page%3D1)。

### 配置

SDK 安装完后，还需要配置环境变量，直接使用下面的明令进行配置：
```
$ cat <<EOF > ~/.zephyrrc
export ZEPHYR_GCC_VARIANT=zephyr
export ZEPHYR_SDK_INSTALL_DIR=/opt/zephyr-sdk
EOF
```

## 获取源码

Zephyr 的代码仓库托管于 Linux 基金会的后台，并采用 Girret 进行管理，这样做的好处是可以非常方便地进行 Code Review。同时，Zephyr 也在 Github 上创建了一个用户([zephyrproject-rtos](https://github.com/zephyrproject-rtos))，用做代码库的镜像。因此我们可以直接到 GitHub 上面下载它的源代码。


- 克隆代码：

`$ git clone https://github.com/zephyrproject-rtos/zephyr.git `


- 直接下载：

[https://github.com/zephyrproject-rtos/zephyr/releases](https://github.com/zephyrproject-rtos/zephyr/releases)

## 编译

进入 Zephyr 的源码目录，然后：
- 执行 source 操作：

`$ source zephyr-env.sh`

- 进入 hello world 目录：

`$ cd samples/hello_world/`

- 编译：

`$ make BOARD=arduino_101`。

其中，参数 BOARD= 用于指定编译的镜像用于哪块开发板。

要查看 Zephyr 支持哪些开发板，直接输入 `make help`：

```
$ make help                  

......

Supported Boards:

  To build an image for one of the supported boards below, run:

  make BOARD=<BOARD NAME>
  in the application directory.

  To flash the image (if supported), run:

  make BOARD=<BOARD NAME> flash
  make BOARD=96b_carbon               - Build for 96b_carbon
  make BOARD=96b_nitrogen             - Build for 96b_nitrogen
  make BOARD=altera_max10             - Build for altera_max10
  make BOARD=arduino_101_ble          - Build for arduino_101_ble
  make BOARD=arduino_101              - Build for arduino_101
  make BOARD=arduino_101_mcuboot      - Build for arduino_101_mcuboot
  make BOARD=arduino_101_sss          - Build for arduino_101_sss
  make BOARD=arduino_due              - Build for arduino_due
  make BOARD=bbc_microbit             - Build for bbc_microbit
  make BOARD=cc2538                   - Build for cc2538
  make BOARD=cc3200_launchxl          - Build for cc3200_launchxl
  make BOARD=curie_ble                - Build for curie_ble
  make BOARD=em_starterkit            - Build for em_starterkit
  make BOARD=frdm_k64f                - Build for frdm_k64f
  make BOARD=frdm_kw41z               - Build for frdm_kw41z
  make BOARD=galileo                  - Build for galileo
  make BOARD=hexiwear_k64             - Build for hexiwear_k64
  make BOARD=minnowboard              - Build for minnowboard
  make BOARD=mps2_an385               - Build for mps2_an385
  make BOARD=nrf51_blenano            - Build for nrf51_blenano
  make BOARD=nrf51_pca10028           - Build for nrf51_pca10028
  make BOARD=nrf52840_pca10056        - Build for nrf52840_pca10056
  make BOARD=nrf52_pca10040           - Build for nrf52_pca10040
  make BOARD=nucleo_f103rb            - Build for nucleo_f103rb
  make BOARD=nucleo_f334r8            - Build for nucleo_f334r8
  make BOARD=nucleo_f401re            - Build for nucleo_f401re
  make BOARD=nucleo_f411re            - Build for nucleo_f411re
  make BOARD=nucleo_l476rg            - Build for nucleo_l476rg
  make BOARD=olimexino_stm32          - Build for olimexino_stm32
  make BOARD=panther                  - Build for panther
  make BOARD=panther_ss               - Build for panther_ss
  make BOARD=qemu_cortex_m3           - Build for qemu_cortex_m3
  make BOARD=qemu_nios2               - Build for qemu_nios2
  make BOARD=qemu_riscv32             - Build for qemu_riscv32
  make BOARD=qemu_x86                 - Build for qemu_x86
  make BOARD=qemu_x86_iamcu           - Build for qemu_x86_iamcu
  make BOARD=quark_d2000_crb          - Build for quark_d2000_crb
  make BOARD=quark_se_c1000_ble       - Build for quark_se_c1000_ble
  make BOARD=quark_se_c1000_devboard  - Build for quark_se_c1000_devboard
  make BOARD=quark_se_c1000_ss_devboard - Build for quark_se_c1000_ss_devboard
  make BOARD=sam_e70_xplained         - Build for sam_e70_xplained
  make BOARD=stm3210c_eval            - Build for stm3210c_eval
  make BOARD=stm32373c_eval           - Build for stm32373c_eval
  make BOARD=stm32_mini_a15           - Build for stm32_mini_a15
  make BOARD=tinytile                 - Build for tinytile
  make BOARD=v2m_beetle               - Build for v2m_beetle
  make BOARD=xt-sim                   - Build for xt-sim
  make BOARD=zedboard_pulpino         - Build for zedboard_pulpino
```

## Hello World

Zephyr 支持使用 QEMU 作为模拟器进行仿真。依然在 hello world 所在目录，执行`make BOARD=qemu_x86 qemu`，然后编译系统会编译程序并运行模拟器：
```
$ make BOARD=qemu_x86 qemu
  ...
  LINK    zephyr.elf
  BIN     zephyr.bin
To exit from QEMU enter: 'CTRL+a, x'
[QEMU] CPU: qemu32
***** BOOTING ZEPHYR OS v1.7.99 - BUILD: Mar 23 2017 13:05:54 *****
Hello World! x86
```

要退出 QEMU 仿真器，请先输入 `CTRL+a`，再输入 `x`。
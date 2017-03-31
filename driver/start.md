# 初识驱动

在前面的《[入门实验 - LED](../get_started/led.md)》中，其实我们已经接触到了驱动相关内容了，只是当时为了让问题简单化，我们有意略过了。在本节中，我们将以该实验为引子，引出 Zephyr 中设备驱动相关内容。涉及到的相关文件：

- samples/basic/blinky/src/main.c
- include/gpio.h
- drivers/gpio/gpio_mcux.c

## 分层思想

在正式看源码前，先简单介绍下 Zephyr 中驱动模型的分层思想。Zephyr 把驱动模型分为三层：

- 应用层，即编写应用程序时所在代码层。
- 接口层，每一类驱动（比如 GPIO、I2C、SPI 等）提供的抽象接口和宏定义。
- 驱动层，具体的驱动代码。

当应用程序需要使用驱动时，会直接调用对应驱动的接口层提供的接口，而不会接触驱动层的具体代码。

> 官方没有在驱动中提分层的相关概念，因此如有不对请指正。

## 源码分析

直接贴源码：
```
#define PORT	      LED0_GPIO_PORT
#define LED	          LED0_GPIO_PIN
#define SLEEP_TIME    1000

void main(void)
{
	int cnt = 0;
	struct device *dev;

	dev = device_get_binding(PORT);
	/* 设置 LED 的引脚为输出 */
	gpio_pin_configure(dev, LED, GPIO_DIR_OUT);

	while (1) {
		/* 每隔1秒设置引脚的电平状态为高/低 */
		gpio_pin_write(dev, LED, cnt % 2);
		cnt++;
		k_sleep(SLEEP_TIME);
	}
```
上面的代码非常简单，主要做了三件事儿：

- 获取设备
- 配置引脚方向
- 每隔一秒设置引脚电平

### 获取设备
```
	struct device *dev;
	dev = device_get_binding(PORT);
```
dev 是用于描述一个驱动设备的结构体的指针，驱动接口层的所有 API 都需要这样一个指针作为入参。PORT 是驱动程序的名字，它的本质是一个字符串。

上面的代码通过驱动的名字 PORT 获取到用于描述该驱动的结构体 dev。那么问题来了，我们怎么知道驱动程序的名字是啥呢？即 PORT 是啥？它是在驱动对应的驱动程序的 Kconfig 文件中定义并配置的。例如，对于 frdm-k64f 这块开发板而言，它的 gpio 驱动是 drivers/gpio/gpio_mucx.c，对应的 Kconfig 文件是同一目录下的 Kconfig.mcux 文件，即 drivers/gpio/Kconfig.mcux。我们可以看看该文件对应的内容：

```
.....
if GPIO_MCUX

config GPIO_MCUX_PORTA
	bool "Port A"
	depends on PINMUX_MCUX_PORTA
	default n
	help
	  Enable Port A.

config GPIO_MCUX_PORTA_NAME
	string "Port A driver name"
	depends on GPIO_MCUX_PORTA
	default "GPIO_0"
......
endif # GPIO_MCUX

```

例如，我们想使用 PORT A 的驱动，则我们传入给 device_get_binding() 的参数则是 CONFIG_GPIO_MCUX_PORTA_NAME （注意，带有一个前缀 CONFIG_，它是编译系统在编译 Kconfig 文件时自动添加的）。

另外，还有一个比较取巧的办法，直接查看编译生成的 .config 文件的内容。例如，对于 frdm-k64f 开发板而言，可以这样查看：

```
zephyr@ubuntu:~/share/zephyr/samples/basic/blinky$ cat outdir/frdm_k64f/.config | grep GPIO
CONFIG_GPIO=y
# CONFIG_GPIO_DW is not set
# CONFIG_GPIO_SCH is not set
CONFIG_GPIO_MCUX=y
CONFIG_GPIO_MCUX_PORTA=y
CONFIG_GPIO_MCUX_PORTA_NAME="GPIO_0" //// 再次证明，驱动的名字是个字符串
CONFIG_GPIO_MCUX_PORTA_PRI=2
CONFIG_GPIO_MCUX_PORTB=y
CONFIG_GPIO_MCUX_PORTB_NAME="GPIO_1"
CONFIG_GPIO_MCUX_PORTB_PRI=2
......
```

### 配置引脚方向
```
gpio_pin_configure(dev, LED, GPIO_DIR_OUT);
```
函数 gpio_pin_configure() 是接口层提供的函数，用来配置 GPIO 的方向，包含三个参数：

- dev，我们之前获取到的描述设备的结构体的指针。
- LED，指明要配置这个 GPIO 端口上的哪个引脚。
- GPIO_DIR_OUT，指定该引脚的方向为输出。这个宏也是在接口层提供的。

### 设置引脚电平

```
	while (1) {
		/* 每隔1秒设置引脚的电平状态为高/低 */
		gpio_pin_write(dev, LED, cnt % 2);
		cnt++;
		k_sleep(SLEEP_TIME);
	}
```
函数 gpio_pin_write() 也是接口层提供的函数，用来配置 GPIO 引脚的电平值，包含三个参数：

- dev，我们之前获取到的描述设备的结构体的指针。
- LED，指明要配置这个 GPIO 端口上的哪个引脚。
- cnt % 2，指定该引脚的输出电平值，0 或 1。

## 总结

通过这个简单的程序，我们能看到在 Zephyr 中利用驱动程序开发应用的一般步骤：

- 通过驱动名获取设备
- 调用接口层提供的接口函数


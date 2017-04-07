# 开发板的选择

到目前为止，Zephyr 已经支持非常多的开发板了，详见 Zephyr 文档 [支持的开发板](http://iot-fans.xyz/zephyr/doc/boards/boards.html)。

如果你手头上正好有上面所列举的一块或多块开发板，可以就直接拿他们学习。如果没有，推荐使用 NXP 的 frdm_k64f（我们今后的实验也主要使用该开发板），原因如下：
- frdm-k64f 是 Zephyr 官方支持得最好的开发板之一（另一个是 Arduino 101）
- 直接用 frdm-k64f 就能完成大部分基础实验
- 直接用 frdm-k64f 就能完成大部分网络实验(自带以太网卡，但是不能进行 ieee 802.15.4 相关实验)
- 直接用 frdm-k64f 就能完成大部分蓝牙实验
- 直接用 frdm-k64f 就能完成 JavaScript 实验
- 直接用 frdm-k64f 就能完成 MicroPython 实验

frdm-k64f 的介绍文档请参考 [NXP FRDM-K64F](http://iot-fans.xyz/zephyr/doc/boards/arm/frdm_k64f/doc/frdm_k64f.html)。

此外，NXP 官方的 [SDK](https://mcuxpresso.nxp.com/en/license?hash=7352a00d5166ebf9cc83f1442c02d98e&hash_download=1) 中也包含很多驱动程序、示例代码，可以用来参考学习。

> 下载前需要注册 NXP 的账号。SDK 下载下来后是一个 .exe 文件，安装后会在安装路径下包含 SDK 的代码（默认路径是 C:\Freescale\KSDK_1.3.0）。

## 烧写程序

对于 frdm-k64f 来说，烧写程序非常简单。只需要一条安卓数据线就既可以完成程序的烧写，还可以当做串口线使用。

<center><img src="./frdm_k64f.jpg" /></center>

用数据线将板子与 PC 连接在一起（板子上的接口为上图的左上角的 USB 口），PC 上面会识别出一个 USB 存储设备，直接将 .bin 文件拷贝到该设备的根目录，然后复位板子，就自动完成烧写了。

此外，PC 上面还会识别出一个 COM 口，我们可以通过它来查看串口输出。

对于其它开发板，请按照板子对应的烧写方式烧写程序。


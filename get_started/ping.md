# 实验 - ping

本节的实验主要演示开发板如何与 PC 机通过网络进行通信。在该实验中，我们将开发板作为 ping 服务端，将 PC 作为客户端，即从 PC 上 ping 开发板。期望的实验现象：
- 从 Windows ping 通开发板
- 从 Ubuntu  Ping 通开发板

## 编译

`samples/net/`目录下的例程是与 net 相关的实验。进入 echo_server 所在目录：
```
$ cd samples/net/echo_server 
$ make BOARD=frdm-k64f
```
编译完成后，生成的镜像文件位于`samples/net/echo_server/outdir/frdk-k64f/zephyr.bin`。

## 硬件连接

## 烧写 

## 现象
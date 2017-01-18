# Zephyr OS 学习笔记

之前看到一句话：好的读书笔记是对一本书的敬意。

越是深入学习，越为 Zephyr 着迷，我也希望献上自己对 Zephyr 的敬意。

## 目录

本系列采用模块化的方式依次学习 Zephyr OS 中的各个主要模块。

- [入门](../../tree/start/): 通过一些简单的应用，激发你对 zephyr 的兴趣；
- [kernel](../../tree/kernel/): 第 2 版 kernel - unified kernel；
- porting: 将 zephyr 移植到 cc2538 的过程；
- driver: 驱动模块；
- usb: usb 专题模块；
- net-arch: 网络协议栈的架构；
- ieee802154: 协议栈 layer 2 中的 ieee 802.15.4；
- 6lowpan: 协议栈中的适配层 6lowpan；
- bluetooth: 协议栈 layer 2 中的 bluetooth；

对于上面的每个模块，都会创建一个新分支，因此请先切换到该分支。 

## 说明
本仓库之前的源文件格式是 markdown，但是为了有更好的阅读体验，现在将其修改为 reStructuredText。

新版学习笔记的在线预览地址：[http://iot-fans.xyz/inside/index.html](http://iot-fans.xyz/inside/index.html)

如果你想看老版本学习笔记的内容，请将分支切换到 [old](../../tree/old)。

## 贡献
如果你想分享关于Zephyr OS 的学习笔记，热烈欢迎，具体细节请参考：[CONTRIBUTION.md](CONTRIBUTION.md)

## 学习交流

QQ 群：580070214

## More
Zephyr 官方提供了非常系统、全面的说明文档，建议多阅读阅读。这里是该文档的中文版：[https://github.com/tidyjiang8/zephyr-doc](https://github.com/tidyjiang8/zephyr-doc) 

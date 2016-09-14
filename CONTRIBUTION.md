# 贡献流程
在 github 上

- 点击仓库右上角的 Fork 图标将仓库 fork 到你自己的账户下

在客户端

- 将你 fork 的仓库 clone 到本地
- 修改文章，提交，并 push 到你的仓库

在 github 上

- 进入你的仓库
- 在仓库下面有个 pull request 链接
- 点击 pull request，然后填写一些说明

# 仓库同步
Q：如何将你的仓库与我的仓库同步？

在客户端

- 进入你本地目录
- git remote add tidyjiang8 https://github.com/tidyjiang8/zephyr-inside.git
- git update
- git merge tidyjiang8
- git push origin master

# 关于文章格式

源文档采用 markdown 格式(.md)，推荐直接使用markdown编辑器编辑文档。

格式的要求：
- 所有段落段首不空格
- 如果需要使用图片，将其放到/images/zephyr/中与源文件对应的目录下(如果该目录不存在，新建该目录)。

另外，为了能直接将 github 下的文章放到博客中，你必须完成如下工作：
- 在文章的合适地方插入新的一行`<!--more-->`，这会在博客的首页生成"阅读全文"字样，如下图所示。

- 在文章的开头，添加一段标识。你只需要修改　title 和　date 两个字段。(注意，title、data的冒号后必须有一个空格)
```
---
title: Zephyr OS nano 内核篇： 执行上下文 // 博客中显示的博客标题，修改为对应的标题
date: 2016-07-28 16:45:35			   // 博客中显示的博客时间，修改为你编写文章的时间
categories: ["Zephyr OS"]			   // 博客的分类。这一项不要修改
tags: [Zephyr]						   // 博客的标签。这一项不要修改
---
```
</center>![](/images/zephyr/contribution/1.png)</center>

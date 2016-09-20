# 贡献流程
在 github 上

- 【步骤1】点击仓库右上角的 Fork 图标将仓库 fork 到你自己的账户下

在客户端

- 【步骤2】将你 fork 的仓库 clone 到本地
- 【步骤3】新建一个分支(假设分支名为`new`)，并切换到该分支
- 【步骤4】在你的`new`分支上修改文章，然后分别执行 git add、git commit 将改动提交到本地库，并记住此次提交的 commit id(假设此次提交生成的commit id 为 `9057042`)
- 【步骤5】切换回`master`分支，先将你本地仓库的`master`分支与我的仓库同步，依次执行：
  - `git remote add tidyjiang8 https://github.com/tidyjiang8/zephyr-inside.git`(这个步骤只需要执行一次，今后再修改文章时不用执行了)
  - `git remote update`
  - `git merge tidyjiang8`
- 【步骤6】将你在你的新分支上修改的东西合并到 master 分支
  - 执行 `git cherry-pick <commit-id>`, 即 `git cherry-pick 9057042`
  
  > 合并`new`分支改动时，我们用`git cherry-pick`命令，而不是`git merge`命令，这样的好处是当你的`new`分支有多次提交时，你可以指定只合并某一次的提交
- 【步骤7】将你的本地 master 分支 push 到你的远程仓库：`git push origin master`

在 github 上

- 【步骤8】进入你的仓库,在仓库下面有个 pull request 链接，点击该链接，然后填写一些说明后提交 PR

在客户端
- 【步骤9】如果你又想修改新文章，先执行【步骤5】将你本地`master`与我的仓库同步
- 【步骤10】切换到你的`new`分支，将本地`master`分支的内容合并到`new`分支：`git merge master`，然后跳转到【步骤4】依次执行

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

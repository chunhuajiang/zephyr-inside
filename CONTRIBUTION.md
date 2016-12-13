# 贡献流程
在 github 上

- 【步骤1】点击仓库右上角的 Fork 图标将仓库 fork 到你自己的账户下

在客户端

> 假设你要修改的分支是`driver`。
 

- 【步骤2】将你 fork 的仓库 clone 到本地
- 【步骤3】新建一个分支(假设分支名为`driver-me`)，并切换到该分支
- 【步骤4】在你的`driver-me`分支上修改文章，然后分别执行 git add、git commit 将改动提交到本地库，并记住此次提交的 commit id(假设此次提交生成的commit id 为 `9057042`)
- 【步骤5】切换回`driver`分支，先将你本地仓库的`driver`分支与我的仓库同步，依次执行：
  - `git remote add tidyjiang8 https://github.com/tidyjiang8/zephyr-inside.git`(这个步骤只需要执行一次，今后再修改文章时不用执行了)
  - `git remote update`
  - `git merge tidyjiang8`
- 【步骤6】将你在你的新分支上修改的东西合并到 driver 分支
  - 执行 `git cherry-pick <commit-id>`, 即 `git cherry-pick 9057042`
  
  > 合并`driver-me`分支改动时，我们用`git cherry-pick`命令，而不是`git merge`命令，这样的好处是当你的`driver-me`分支有多次提交时，你可以指定只合并某一次的提交
- 【步骤7】将你的本地 driver 分支 push 到你的远程仓库：`git push origin driver`

在 github 上

- 【步骤8】进入你的仓库,在仓库下面有个 pull request 链接，点击该链接，然后填写一些说明后提交 PR

在客户端
- 【步骤9】如果你又想修改新文章，先执行【步骤5】将你本地`driver`与我的仓库同步
- 【步骤10】切换到你的`driver-me`分支，将本地`driver`分支的内容合并到`driver-me`分支：`git merge driver`，然后跳转到【步骤4】依次执行

# 关于文章格式

源文档采用 reStructuredText 格式(.rst)，如果您不熟悉该语法，不要担心，看看我已有文章的内容的格式就可以了。如果还有特殊需求，可以在网上搜索，或者直接在群里提问。

格式的要求：
- 所有段落段首不空格
- 如果需要使用图片，将其放到/images/zephyr/中与源文件对应的目录下(如果该目录不存在，新建该目录)。

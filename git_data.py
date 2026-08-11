# -*- coding: utf-8 -*-
"""
Git 命令速查 · 内置初始数据
数据结构：{"category": 分类, "command": 命令, "note": 注释}
来源：git使用速查.md / git命令速查.md / git学习总结.md
"""

# 内置数据（首次运行时写入用户数据文件；之后用户可自由增删改）
DEFAULT_ITEMS = [
    # ---------- 配置 ----------
    {"category": "配置", "command": "git config --global user.name \"Luiax\"",
     "note": "设置名字（只需一次）"},
    {"category": "配置", "command": "git config --global user.email \"2105334546@qq.com\"",
     "note": "设置邮箱（只需一次，需与 GitHub 绑定邮箱一致）"},
    {"category": "配置", "command": "git config --global --list",
     "note": "查看所有配置"},
    {"category": "配置", "command": "git config --global core.quotepath false",
     "note": "中文文件名正常显示"},
    {"category": "配置", "command": "git config --get core.quotepath",
     "note": "验证某个配置的值"},
    {"category": "配置", "command": "git init",
     "note": "把当前文件夹变成 git 仓库（只需一次）"},
    {"category": "配置", "command": "git --version",
     "note": "查看 git 版本"},
    {"category": "配置", "command": "git help 命令名",
     "note": "查看某个命令的帮助"},

    # ---------- 查看 ----------
    {"category": "查看", "command": "git status",
     "note": "当前状态：有哪些改动/新文件"},
    {"category": "查看", "command": "git status --short",
     "note": "精简版状态（M=已修改 ??=未跟踪）"},
    {"category": "查看", "command": "git log --oneline",
     "note": "提交历史，一行一条"},
    {"category": "查看", "command": "git log --oneline -5",
     "note": "只看最近 5 条提交"},
    {"category": "查看", "command": "git log",
     "note": "完整详情（提交号/作者/时间/说明）"},
    {"category": "查看", "command": "git diff",
     "note": "查看未存档的改动内容（逐行）"},
    {"category": "查看", "command": "git diff 提交号 -- 文件名",
     "note": "对比某版本和当前文件"},
    {"category": "查看", "command": "git show 提交号",
     "note": "查看某次提交改了什么，如 git show 6f64556"},
    {"category": "查看", "command": "git show 提交号:文件名",
     "note": "查看某版本的文件内容（不修改文件）"},
    {"category": "查看", "command": "git show 提交号 --stat",
     "note": "查看某次提交改了哪些文件"},
    {"category": "查看", "command": "git ls-files",
     "note": "列出仓库里所有被跟踪的文件"},

    # ---------- 存档 ----------
    {"category": "存档", "command": "git add .",
     "note": "暂存全部改动（. = 当前文件夹所有）"},
    {"category": "存档", "command": "git add 文件名",
     "note": "只暂存某个文件，如 git add snake.html"},
    {"category": "存档", "command": "git commit -m \"说明文字\"",
     "note": "正式存档（必须带 -m 和说明），如 git commit -m \"修复撞墙判定的bug\""},

    # ---------- 回滚 ----------
    {"category": "回滚", "command": "git checkout -- 文件名",
     "note": "撤销某个文件的改动（回到最近一次存档）"},
    {"category": "回滚", "command": "git reset",
     "note": "取消暂存（文件保留，重新 add 即可）"},
    {"category": "回滚", "command": "git revert 提交号",
     "note": "撤销某次提交：生成一个新提交抵消它，历史保留"},
    {"category": "回滚", "command": "git reset --hard HEAD~1",
     "note": "⚠️ 危险：彻底删除最近 1 个提交及改动，慎用"},
    {"category": "回滚", "command": "git checkout 提交号 -- 文件名",
     "note": "用历史版本覆盖当前文件，可找回被删/改坏的文件（先 add+commit 再操作）"},
    {"category": "回滚", "command": "git checkout 提交号",
     "note": "整个目录回到过去（看完要 checkout master 回来）"},

    # ---------- 分支 ----------
    {"category": "分支", "command": "git branch",
     "note": "查看所有分支（* 号是当前分支）"},
    {"category": "分支", "command": "git branch 新分支名",
     "note": "创建分支（复制当前状态）"},
    {"category": "分支", "command": "git checkout 新分支名",
     "note": "切换到该分支"},
    {"category": "分支", "command": "git checkout -b 新分支名",
     "note": "创建并切换分支（一步到位）"},
    {"category": "分支", "command": "git merge 新分支名",
     "note": "把该分支合并到当前分支"},
    {"category": "分支", "command": "git branch -d 新分支名",
     "note": "删除分支（已合并后）"},
    {"category": "分支", "command": "git checkout master",
     "note": "切回主线分支"},

    # ---------- 远程 ----------
    {"category": "远程", "command": "git clone https://github.com/用户名/仓库名.git",
     "note": "下载别人的/自己的项目"},
    {"category": "远程", "command": "git remote add origin https://github.com/用户名/仓库名.git",
     "note": "关联远程仓库（首次）"},
    {"category": "远程", "command": "git push -u origin master",
     "note": "第一次推送到 GitHub"},
    {"category": "远程", "command": "git push",
     "note": "之后推送"},
    {"category": "远程", "command": "git pull",
     "note": "拉取远程最新代码"},

    # ---------- 其他常用 ----------
    {"category": "其他常用", "command": "cd D:\\Rxm\\实验",
     "note": "进入工作区（按自己项目路径改）"},
    {"category": "其他常用", "command": "notepad 文件名",
     "note": "用记事本打开文件"},
    {"category": "其他常用", "command": "start 文件名",
     "note": "用默认程序打开文件"},
    {"category": "其他常用", "command": "explorer .",
     "note": "打开资源管理器（当前文件夹）"},
    {"category": "其他常用", "command": "git add .gitignore && git commit -m \"添加忽略规则\"",
     "note": "写 .gitignore 后让它生效"},

    # ---------- 常见报错 ----------
    {"category": "常见报错", "command": "Author identity unknown",
     "note": "没配名字/邮箱 → 运行配置区的两条 git config 命令"},
    {"category": "常见报错", "command": "fatal: not a git repository",
     "note": "当前目录不是仓库 → cd 进工作区，或 git init"},
    {"category": "常见报错", "command": "error: failed to push",
     "note": "远程有更新/没权限 → 先 git pull 再 push；检查账号权限"},
    {"category": "常见报错", "command": "Nothing specified, nothing added",
     "note": "git add 后面漏了 . → 写 git add ."},
    {"category": "常见报错", "command": "nothing to commit",
     "note": "没有新改动 → 正常，改完代码再来"},
    {"category": "常见报错", "command": "warning: LF will be replaced by CRLF",
     "note": "Windows 换行符提示 → 无害，忽略"},
]

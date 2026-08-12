# 🚀 Git 命令速查

一个开箱即用的 **Git 指令速查桌面应用**：内置常用 git 命令与注释，支持搜索、一键复制、自行增改，还带 **DeepSeek AI 问答** 和 **本地模糊搜索**——描述你想做的事，立刻得到对应的 git 指令。

> 纯本地便携版：单文件 exe，无需安装 Python，双击即用。

---

## ✨ 功能特性

| 功能 | 说明 |
|---|---|
| 📂 **分类浏览** | 配置 / 查看 / 存档 / 回滚 / 分支 / 远程 / 其他常用 / 常见报错，8 大分类 |
| 🔍 **实时搜索** | 顶部搜索框按命令 / 注释 / 分类即时过滤（`Ctrl+F` 聚焦） |
| 📋 **一键复制** | 点击任意命令卡片即复制到剪贴板 |
| ➕ **自行增改** | 添加 / 编辑 / 删除命令，数据存本地 `git_data.json`，可备份分享 |
| 🤖 **AI 问答** | 对接 DeepSeek，用自然语言描述需求，AI 参考你的本地指令库给出命令 |
| 🎯 **本地模糊搜索** | 不联网也能用：中文 2-gram + 英文词模糊匹配，列出疑似指令 |
| ⚡ **一键添加 AI 指令** | AI 回答中的 git 指令可批量解析入库，自动匹配分类、提取注释 |
| 💾 **持久化** | 所有增删改自动保存，重启不丢；首次运行自动生成内置 51 条指令 |

---

## 📸 界面预览

**命令速查页**（分类浏览 + 搜索 + 一键复制）：

![命令速查页](screenshots/tab_commands.png)

**AI 问答页**（DeepSeek 回答 + 本地疑似指令 + 一键添加）：

![AI 问答页](screenshots/tab_ai.png)

---

## 🚀 快速开始

### 方式一：直接下载 exe（推荐，免安装）

1. 下载 `dist/Git命令速查.exe`
2. 放到任意目录（**不要放 `C:\Program Files` 等只读目录**），双击运行
3. 完成 🎉

> 需要 64 位 Windows（Win10 / Win11）。首次启动稍慢属正常（程序自解压）。

### 方式二：从源码运行

```powershell
# 需要 Python 3.8+（自带 tkinter）
python main.py
```

---

## 🧩 使用说明

### 命令速查页
- 左侧点分类过滤，右侧显示对应命令卡片
- 顶部搜索框输入关键词实时过滤
- 点卡片任意处 / 「复制」按钮复制命令
- 「＋ 添加命令」自定义指令；卡片右侧可编辑、删除

### AI 问答页
1. 点「⚙ 设置 API Key」填入你的 DeepSeek API Key
   （在 https://platform.deepseek.com 申请，保存在同目录 `config.json`）
2. 输入问题，如"我想撤销上次提交"，回车
3. 右侧「疑似指令」即时显示本地模糊匹配结果（无需网络）
4. AI 回答后点「＋ 一键添加指令」可将新指令批量加入本地库（自动分类、自动跳过已存在的）

### 数据文件
| 文件 | 说明 |
|---|---|
| `git_data.json` | 指令库（增删改都存这里，可备份 / 分享） |
| `config.json` | DeepSeek API Key（含密钥，**请勿公开分享**） |

---

## 🔨 自行打包 exe

```powershell
pip install pyinstaller
python -m PyInstaller GitCheatsheet.spec --noconfirm --distpath dist --workpath build
```

重新生成图标（可选）：

```powershell
python make_icon.py   # 生成 icon.ico / icon.png 后重新打包
```

---

## 📁 项目结构

```
├── main.py              # 主程序（GUI + AI 问答 + 模糊搜索）
├── git_data.py          # 内置指令数据（51 条，按分类）
├── GitCheatsheet.spec   # PyInstaller 打包配置
├── make_icon.py         # 图标生成脚本
├── icon.ico / icon.png  # 应用图标
├── dist/
│   └── Git命令速查.exe  # 打包好的可执行文件
└── screenshots/         # 界面截图
```

---

## ⚙️ 技术栈

- **Python 3** + **tkinter**（标准库 GUI，零第三方依赖）
- **urllib** 调用 DeepSeek API（`deepseek-chat`）
- **PyInstaller** 单文件打包
- 本地模糊搜索：difflib 相似度 + 中文 2-gram 分词

---

## ⚠️ 注意事项

- 杀毒软件可能对 PyInstaller 打包的 exe 误报，添加信任即可
- `git reset --hard` 等危险命令的注释已标注 ⚠️，使用前请确认
- AI 功能需联网；本地搜索 / 命令浏览完全离线可用

---

*Made with ❤️ for everyday Git users*

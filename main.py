# -*- coding: utf-8 -*-
"""
Git 命令速查（桌面版）
- 内置常用 git 命令 + 注释，按分类浏览
- 支持搜索、一键复制、自己添加/编辑/删除
- 数据保存在 exe 同目录的 git_data.json
"""

import difflib
import json
import os
import re
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

from git_data import DEFAULT_ITEMS

# DeepSeek API
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ---------------- 主题配色 ----------------
COLORS = {
    "bg": "#14141f",
    "bg2": "#1a1a2e",
    "bg3": "#232345",
    "card": "#20203a",
    "card_hover": "#26264a",
    "border": "#33335a",
    "text": "#e8e8f0",
    "dim": "#9a9ab8",
    "accent": "#4ecca3",
    "accent_dim": "#2f8f72",
    "danger": "#e74c6f",
    "warn": "#f5b942",
    "input_bg": "#10101c",
}

CATEGORY_ORDER = ["配置", "查看", "存档", "回滚", "分支", "远程", "其他常用", "常见报错"]


def data_dir():
    """数据文件放在 exe / 脚本所在目录"""
    if getattr(sys, "frozen", False):  # 打包后的 exe
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_path():
    return os.path.join(data_dir(), "git_data.json")


def load_items():
    """读取用户数据；不存在则用内置数据初始化"""
    path = data_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    # 首次运行：写一份默认数据到文件
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_ITEMS, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return list(DEFAULT_ITEMS)


def save_items(items):
    try:
        with open(data_path(), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def all_categories(items):
    cats = []
    for it in items:
        c = it.get("category", "未分类")
        if c not in cats:
            cats.append(c)
    # 内置分类按固定顺序，其余按出现顺序
    ordered = [c for c in CATEGORY_ORDER if c in cats]
    ordered += [c for c in cats if c not in ordered]
    return ordered


# ---------------- 配置（API Key） ----------------
def config_path():
    return os.path.join(data_dir(), "config.json")


def load_config():
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(cfg):
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


# ---------------- 本地模糊搜索 ----------------
def _zh_bigrams(text):
    """连续中文切 2-gram：'撤销提交' -> ['撤销','销提','提交']"""
    grams = []
    for m in re.findall(r"[\u4e00-\u9fff]+", text.lower()):
        if len(m) == 1:
            grams.append(m)
        else:
            grams.extend(m[i:i + 2] for i in range(len(m) - 1))
    return grams


def _query_tokens(q):
    """查询词拆 token：英文单词/数字 + 中文 2-gram"""
    eng = re.findall(r"[a-z0-9_\-.]+", q.lower())
    return eng + _zh_bigrams(q)


def fuzzy_search(items, query, top_n=6):
    """
    在本地指令库中做模糊搜索：
      - 整串子串命中（最高权重）
      - 查询 token（英文词 + 中文 2-gram）命中覆盖率
      - 字符串相似度（difflib，辅助）
    返回按得分降序的条目列表。
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    tokens = _query_tokens(q)
    total_len = sum(len(t) for t in tokens) or 1
    scored = []
    for it in items:
        cmd = it.get("command", "")
        note = it.get("note", "")
        cat = it.get("category", "")
        hay = f"{cat} {cmd} {note}".lower()

        score = 0.0
        if q in hay:                      # 整串子串命中
            score += 3.0
        hit_len = sum(len(t) for t in tokens if t in hay)
        score += 1.5 * min(hit_len / total_len, 1.0)
        score += 0.5 * difflib.SequenceMatcher(None, q, hay).ratio()

        if score >= 0.5:
            scored.append((score, it))
    scored.sort(key=lambda x: -x[0])
    return [it for _, it in scored[:top_n]]


# ---------------- AI 回答解析（一键添加） ----------------
def _split_inline_comment(line):
    """拆分行内注释：'git commit -m "x"  # 说明' -> ('git commit -m "x"', '说明')"""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return line[:i].strip(), line[i + 1:].strip()
    return line.strip(), ""


def parse_ai_commands(text):
    """
    从 AI 回答文本中解析 git 指令：
      - 提取 ``` 代码块中的命令（每行一条，支持行内 # 注释）
      - 代码块后面的说明文字作为该组命令的注释
    返回 [{command, note}]，去重保留顺序。
    """
    if not text:
        return []
    results = []
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if line.startswith("```"):
            # 收集代码块
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                s = lines[i].strip()
                if s:
                    block.append(s)
                i += 1
            i += 1  # 跳过结束 ```
            # 代码块后的说明文字（到下一个代码块 / 空行太多为止）
            note_lines = []
            blank = 0
            while i < n and not lines[i].strip().startswith("```"):
                s = lines[i].strip()
                if not s:
                    blank += 1
                    if blank >= 2:
                        break
                    i += 1
                    continue
                blank = 0
                note_lines.append(s)
                i += 1
            note = " ".join(note_lines).strip()

            for raw in block:
                cmd, inline_note = _split_inline_comment(raw)
                # 去掉行首可能出现的提示符
                for prefix in ("$", ">", "PS>", "C:\\", "powershell"):
                    if cmd.startswith(prefix):
                        cmd = cmd[len(prefix):].strip()
                if not cmd or not cmd.startswith("git"):
                    continue
                results.append({"command": cmd,
                                "note": inline_note or note})
            continue
        i += 1

    # 去重（同一命令保留第一条，注释尽量非空）
    seen, out = set(), []
    for it in results:
        if it["command"] in seen:
            continue
        seen.add(it["command"])
        out.append(it)
    return out


def guess_category(command):
    """根据命令内容自动匹配分类（与内置分类一致）"""
    c = command.lower()
    if any(k in c for k in ("config", "init", "--version")):
        return "配置"
    if any(k in c for k in ("status", "log", "diff", "show", "ls-files", "help")):
        return "查看"
    if any(k in c for k in ("add", "commit")):
        return "存档"
    if "checkout --" in c or "restore" in c or "reset" in c or "revert" in c:
        return "回滚"
    if any(k in c for k in ("branch", "merge", "switch", "checkout -b")):
        return "分支"
    if any(k in c for k in ("clone", "push", "pull", "remote", "fetch")):
        return "远程"
    return "其他常用"


# ---------------- DeepSeek API ----------------
def ask_deepseek(api_key, question, items):
    """
    调用 DeepSeek chat API。
    返回 (ok, text, error_msg)。
    """
    if not api_key:
        return False, "", "未配置 API Key"

    # 组装本地指令库上下文，让 AI 优先给出疑似指令
    lib_lines = []
    for it in items:
        lib_lines.append(f"- {it.get('command', '')} ｜ {it.get('note', '')}")
    lib_text = "\n".join(lib_lines)

    system_prompt = (
        "你是 Git 命令速查助手，用户会用中文描述想做的事。\n"
        "请先参考用户本地的 git 指令库，挑选最合适的一条或多条指令回答；"
        "若本地没有，可补充通用 git 命令并注明「额外建议」。\n"
        "回答格式：先给出命令（放在 ``` 代码块里），再写一句中文说明。"
        "危险命令（如 git reset --hard）必须标注 ⚠️。\n"
        f"本地指令库：\n{lib_text}"
    )

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "stream": False,
        "max_tokens": 1000,
        "temperature": 0.3,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_API_URL, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return True, data["choices"][0]["message"]["content"].strip(), ""
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        hint = {401: "API Key 无效", 402: "余额不足", 429: "请求过于频繁"}.get(e.code, f"HTTP {e.code}")
        return False, "", f"{hint}：{detail}"
    except (urllib.error.URLError, OSError) as e:
        return False, "", f"网络错误：{e}"
    except (KeyError, ValueError) as e:
        return False, "", f"返回格式异常：{e}"


# ---------------- GUI ----------------
class App:
    TITLE = "Git 命令速查"

    def __init__(self, root):
        self.root = root
        root.title(self.TITLE)
        root.geometry("900x640")
        root.minsize(720, 480)
        root.configure(bg=COLORS["bg"])

        self.ui_font = tkfont.Font(family="Microsoft YaHei UI", size=10)
        self.ui_font_bold = tkfont.Font(family="Microsoft YaHei UI", size=10, weight="bold")
        self.mono_font = tkfont.Font(family="Consolas", size=10)
        self.mono_font_bold = tkfont.Font(family="Consolas", size=10, weight="bold")

        self.items = load_items()
        self.current_cat = "全部"
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())

        self._build()
        self.refresh()
        self.set_status(f"共 {len(self.items)} 条命令 · 数据文件：{data_path()}")

    # ---------- 界面搭建 ----------
    def _build(self):
        # 顶部工具栏
        toolbar = tk.Frame(self.root, bg=COLORS["bg2"], padx=16, pady=10)
        toolbar.pack(fill="x")
        tk.Label(toolbar, text="Git 命令速查", font=self.ui_font_bold,
                 fg=COLORS["accent"], bg=COLORS["bg2"]).pack(side="left")
        tk.Label(toolbar, text=" 日常指令 + 注释，可自行增改",
                 font=self.ui_font, fg=COLORS["dim"], bg=COLORS["bg2"]).pack(side="left", padx=(8, 0))

        btn_add = tk.Button(toolbar, text="＋ 添加命令", command=self.add_item,
                            font=self.ui_font, bg=COLORS["accent"], fg="#10101c",
                            activebackground=COLORS["accent_dim"], activeforeground="#ffffff",
                            relief="flat", padx=14, pady=4, cursor="hand2")
        btn_add.pack(side="right")

        # 搜索框
        search_box = tk.Frame(toolbar, bg=COLORS["bg2"])
        search_box.pack(side="right", padx=10)
        self.search_entry = tk.Entry(search_box, textvariable=self.search_var,
                                     font=self.ui_font, bg=COLORS["input_bg"],
                                     fg=COLORS["text"], insertbackground=COLORS["text"],
                                     relief="flat", width=26)
        self.search_entry.pack(side="left", ipady=4, ipadx=6)
        self.search_entry.insert(0, "")
        tk.Label(search_box, text="🔍", bg=COLORS["bg2"], fg=COLORS["dim"]).pack(side="left", padx=(6, 0))

        # 主体：Notebook 双标签（命令速查 / AI 问答）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # ---- Tab 1：命令速查（原分类 + 列表） ----
        self.tab_cmd = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.tab_cmd, text="  命令速查  ")

        body = self.tab_cmd

        # 左侧分类栏
        side = tk.Frame(body, bg=COLORS["bg2"], width=170)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="分类", font=self.ui_font_bold,
                 fg=COLORS["dim"], bg=COLORS["bg2"]).pack(anchor="w", padx=14, pady=(12, 6))

        self.cat_list = tk.Listbox(side, font=self.ui_font, bg=COLORS["bg2"], fg=COLORS["text"],
                                   selectbackground=COLORS["accent"], selectforeground="#10101c",
                                   relief="flat", highlightthickness=0, activestyle="none",
                                   exportselection=False, bd=0)
        self.cat_list.pack(fill="both", expand=True, padx=6, pady=(0, 12))
        self.cat_list.bind("<<ListboxSelect>>", self._on_cat_select)

        # 右侧内容区
        content = tk.Frame(body, bg=COLORS["bg"])
        content.pack(side="left", fill="both", expand=True)

        # 提示条
        hint = tk.Label(content, text="点击命令即可复制到剪贴板",
                        font=self.ui_font, fg=COLORS["dim"], bg=COLORS["bg"], anchor="w")
        hint.pack(fill="x", padx=16, pady=(10, 4))

        # 滚动列表容器
        list_frame = tk.Frame(content, bg=COLORS["bg"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.canvas = tk.Canvas(list_frame, bg=COLORS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.card_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self._card_window = self.canvas.create_window((0, 0), window=self.card_frame, anchor="nw")
        self.card_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._card_window, width=e.width))
        # 鼠标滚轮（只在命令速查页生效，AI 页文本框独立滚动）
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Escape>", lambda e: self.search_entry.delete(0, "end"))

        # ---- Tab 2：AI 问答 ----
        self.tab_ai = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.tab_ai, text="  🤖 AI 问答  ")
        self._build_ai_tab()

        # 底部状态栏
        status_bar = tk.Frame(self.root, bg=COLORS["bg3"], padx=12, pady=4)
        status_bar.pack(fill="x")
        self.status_label = tk.Label(status_bar, text="", font=self.ui_font,
                                     fg=COLORS["dim"], bg=COLORS["bg3"], anchor="w")
        self.status_label.pack(fill="x")

    def _build_ai_tab(self):
        """AI 问答页：问题输入 + AI 回答 + 本地模糊搜索结果"""
        pad = {"padx": 16}
        frm = tk.Frame(self.tab_ai, bg=COLORS["bg"])
        frm.pack(fill="both", expand=True, **pad)

        # 顶部：标题 + 设置
        top = tk.Frame(frm, bg=COLORS["bg"])
        top.pack(fill="x", pady=(10, 4))
        tk.Label(top, text="AI 问答（DeepSeek）", font=self.ui_font_bold,
                 fg=COLORS["accent"], bg=COLORS["bg"]).pack(side="left")
        tk.Label(top, text=" 描述你想做的事，AI 返回对应 git 指令",
                 font=self.ui_font, fg=COLORS["dim"], bg=COLORS["bg"]).pack(side="left", padx=(8, 0))
        tk.Button(top, text="⚙ 设置 API Key", command=self._set_api_key,
                  font=self.ui_font, bg=COLORS["bg3"], fg=COLORS["dim"],
                  activebackground=COLORS["bg3"], activeforeground=COLORS["text"],
                  relief="flat", padx=10, cursor="hand2").pack(side="right")

        # 问题输入行
        qrow = tk.Frame(frm, bg=COLORS["bg"])
        qrow.pack(fill="x", pady=(4, 8))
        self.ai_question = tk.Entry(qrow, font=self.ui_font, bg=COLORS["input_bg"],
                                    fg=COLORS["text"], insertbackground=COLORS["text"],
                                    relief="flat")
        self.ai_question.pack(side="left", fill="x", expand=True, ipady=6, ipadx=6)
        self.ai_question.bind("<Return>", lambda e: self.ask_ai())
        tk.Button(qrow, text="发送 (Enter)", command=self.ask_ai,
                  font=self.ui_font, bg=COLORS["accent"], fg="#10101c",
                  activebackground=COLORS["accent_dim"], activeforeground="#ffffff",
                  relief="flat", padx=16, cursor="hand2").pack(side="left", padx=(8, 0))

        # 上下分栏：AI 回答 / 疑似指令
        panes = tk.Frame(frm, bg=COLORS["bg"])
        panes.pack(fill="both", expand=True, pady=(0, 10))

        # 左栏：AI 回答
        left = tk.Frame(panes, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True)
        lhead = tk.Frame(left, bg=COLORS["bg"])
        lhead.pack(fill="x", pady=(0, 4))
        tk.Label(lhead, text="💬 AI 回答", font=self.ui_font_bold,
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(side="left")
        tk.Button(lhead, text="＋ 一键添加指令", command=self.add_from_ai,
                  font=("Microsoft YaHei UI", 9), bg=COLORS["accent"], fg="#10101c",
                  activebackground=COLORS["accent_dim"], activeforeground="#ffffff",
                  relief="flat", padx=10, cursor="hand2").pack(side="right", padx=(6, 0))
        tk.Button(lhead, text="复制回答", command=self.copy_ai_answer,
                  font=("Microsoft YaHei UI", 9), bg=COLORS["bg3"], fg=COLORS["dim"],
                  activebackground=COLORS["bg3"], activeforeground=COLORS["text"],
                  relief="flat", padx=8, cursor="hand2").pack(side="right")

        ai_wrap = tk.Frame(left, bg=COLORS["card"], bd=0)
        ai_wrap.pack(fill="both", expand=True)
        self.ai_answer = tk.Text(ai_wrap, font=self.ui_font, bg=COLORS["card"],
                                 fg=COLORS["text"], relief="flat", wrap="word",
                                 padx=10, pady=8, state="disabled", height=16)
        self.ai_answer.pack(side="left", fill="both", expand=True)
        ai_sb = ttk.Scrollbar(ai_wrap, orient="vertical", command=self.ai_answer.yview)
        ai_sb.pack(side="right", fill="y")
        self.ai_answer.configure(yscrollcommand=ai_sb.set)

        # 右栏：疑似指令（本地模糊搜索）
        right = tk.Frame(panes, bg=COLORS["bg"], width=330)
        right.pack(side="right", fill="both", expand=False, padx=(12, 0))
        right.pack_propagate(False)
        rhead = tk.Frame(right, bg=COLORS["bg"])
        rhead.pack(fill="x", pady=(0, 4))
        tk.Label(rhead, text="🎯 疑似指令（本地模糊匹配）", font=self.ui_font_bold,
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(side="left")

        self.fuzzy_list = tk.Listbox(right, font=self.mono_font, bg=COLORS["card"],
                                     fg=COLORS["text"], selectbackground=COLORS["accent"],
                                     selectforeground="#10101c", relief="flat",
                                     highlightthickness=0, activestyle="none",
                                     exportselection=False, bd=0, height=16)
        self.fuzzy_list.pack(fill="both", expand=True)
        self.fuzzy_list.bind("<Double-Button-1>", self._copy_fuzzy_selected)
        tk.Label(right, text="双击列表项复制命令；本地匹配无需网络，AI 回答需要 API Key",
                 font=("Microsoft YaHei UI", 9), fg=COLORS["dim"], bg=COLORS["bg"],
                 anchor="w", justify="left", wraplength=300).pack(fill="x", pady=(4, 0))

    # ---------- 数据展示 ----------
    def refresh(self):
        """根据当前分类 + 搜索词刷新列表"""
        # 重建分类栏
        self.cat_list.delete(0, "end")
        cats = ["全部"] + all_categories(self.items)
        for c in cats:
            self.cat_list.insert("end", c)
        if self.current_cat in cats:
            self.cat_list.selection_clear(0, "end")
            self.cat_list.selection_set(cats.index(self.current_cat))
        else:
            self.current_cat = "全部"
            self.cat_list.selection_set(0)

        # 过滤
        kw = self.search_var.get().strip().lower()
        shown = 0
        for child in self.card_frame.winfo_children():
            child.destroy()

        for it in self.items:
            cat = it.get("category", "未分类")
            cmd = it.get("command", "")
            note = it.get("note", "")
            if self.current_cat != "全部" and cat != self.current_cat:
                continue
            if kw:
                hay = f"{cat} {cmd} {note}".lower()
                if kw not in hay:
                    continue
            self._add_card(it)
            shown += 1

        if shown == 0:
            empty = tk.Label(self.card_frame, text="没有匹配的命令，试试换个关键词，或点右上角「＋ 添加命令」",
                             font=self.ui_font, fg=COLORS["dim"], bg=COLORS["bg"])
            empty.pack(fill="x", padx=8, pady=30)

    def _add_card(self, item):
        cat = item.get("category", "未分类")
        cmd = item.get("command", "")
        note = item.get("note", "")

        card = tk.Frame(self.card_frame, bg=COLORS["card"], bd=0)
        card.pack(fill="x", padx=4, pady=4)

        # 分类徽标 + 命令
        head = tk.Frame(card, bg=COLORS["card"])
        head.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(head, text=cat, font=("Microsoft YaHei UI", 9),
                 fg=COLORS["accent"], bg=COLORS["card"]).pack(side="left")
        tk.Label(head, text=cmd, font=self.mono_font_bold,
                 fg=COLORS["text"], bg=COLORS["card"], anchor="w").pack(side="left", padx=(12, 0))

        # 右侧操作按钮
        btn_edit = tk.Button(head, text="编辑", command=lambda i=item: self.edit_item(i),
                             font=("Microsoft YaHei UI", 9), bg=COLORS["bg3"], fg=COLORS["dim"],
                             activebackground=COLORS["bg3"], activeforeground=COLORS["text"],
                             relief="flat", padx=8, cursor="hand2")
        btn_edit.pack(side="right")
        btn_del = tk.Button(head, text="删除", command=lambda i=item: self.delete_item(i),
                            font=("Microsoft YaHei UI", 9), bg=COLORS["bg3"], fg=COLORS["danger"],
                            activebackground=COLORS["bg3"], activeforeground=COLORS["danger"],
                            relief="flat", padx=8, cursor="hand2")
        btn_del.pack(side="right", padx=(4, 0))
        btn_copy = tk.Button(head, text="复制", command=lambda c=cmd: self.copy_command(c),
                             font=("Microsoft YaHei UI", 9), bg=COLORS["accent_dim"], fg="#ffffff",
                             activebackground=COLORS["accent"], activeforeground="#10101c",
                             relief="flat", padx=10, cursor="hand2")
        btn_copy.pack(side="right", padx=(4, 0))

        # 注释
        if note:
            tk.Label(card, text=note, font=self.ui_font, fg=COLORS["dim"],
                     bg=COLORS["card"], anchor="w", justify="left", wraplength=620).pack(
                fill="x", padx=12, pady=(0, 8))

        # 整卡点击复制（避开按钮）
        for w in (card, head):
            w.bind("<Button-1>", lambda e, c=cmd: self.copy_command(c))

        # 悬停效果
        def on_enter(e):
            card.configure(bg=COLORS["card_hover"])
            for w in card.winfo_children():
                w.configure(bg=COLORS["card_hover"])

        def on_leave(e):
            card.configure(bg=COLORS["card"])
            for w in card.winfo_children():
                w.configure(bg=COLORS["card"])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    # ---------- 事件 ----------
    def _on_cat_select(self, event):
        sel = self.cat_list.curselection()
        if sel:
            self.current_cat = self.cat_list.get(sel[0])
            self.refresh()

    def _on_wheel(self, event):
        # 只在命令速查页生效；AI 页的文本框自己处理滚动
        if self.notebook.select() != str(self.tab_cmd):
            return None
        if self.canvas.winfo_height() < self.card_frame.winfo_reqheight():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    # ---------- AI 问答 ----------
    def _set_ai_text(self, text):
        self.ai_answer.configure(state="normal")
        self.ai_answer.delete("1.0", "end")
        self.ai_answer.insert("1.0", text)
        self.ai_answer.configure(state="disabled")

    def _set_api_key(self):
        cfg = load_config()
        cur = cfg.get("api_key", "")
        key = simpledialog.askstring(
            "DeepSeek API Key",
            "输入你的 DeepSeek API Key（留空则清除）：\n可在 https://platform.deepseek.com 申请",
            initialvalue=cur, show="*", parent=self.root)
        if key is None:
            return
        cfg["api_key"] = key.strip()
        if save_config(cfg):
            self.set_status("✅ API Key 已保存" if key.strip() else "已清除 API Key")
        else:
            self.set_status("⚠️ 保存 API Key 失败：config.json 不可写")

    def ask_ai(self):
        q = self.ai_question.get().strip()
        if not q:
            self.set_status("请先输入问题")
            return

        # 本地模糊搜索：立即展示疑似指令
        results = fuzzy_search(self.items, q)
        self.fuzzy_list.delete(0, "end")
        if results:
            for it in results:
                cmd = it.get("command", "")
                note = it.get("note", "")
                self.fuzzy_list.insert("end", f"{cmd}  ｜ {note}")
            self.fuzzy_list.selection_set(0)
            self.set_status(f"本地匹配到 {len(results)} 条疑似指令，正在请求 AI…")
        else:
            self.fuzzy_list.insert("end", "（本地未匹配到，等待 AI 回答…）")
            self.set_status("本地未匹配到指令，正在请求 AI…")

        cfg = load_config()
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            self._set_ai_text("⚠️ 未配置 DeepSeek API Key。\n\n请点右上角「⚙ 设置 API Key」填入你的 key（https://platform.deepseek.com 申请）。\n\n左侧「疑似指令」是本地模糊匹配结果，无需网络即可使用。")
            self.set_status("未配置 API Key，仅显示本地匹配结果")
            return

        self._set_ai_text("🤔 正在思考…")
        threading.Thread(target=self._ask_worker, args=(api_key, q), daemon=True).start()

    def _ask_worker(self, api_key, question):
        ok, text, err = ask_deepseek(api_key, question, self.items)
        self.root.after(0, lambda: self._on_ai_result(ok, text, err))

    def _on_ai_result(self, ok, text, err):
        if ok:
            self._set_ai_text(text)
            self.set_status("✅ AI 回答完成，点击命令可直接复制")
        else:
            self._set_ai_text(f"❌ AI 请求失败：{err}\n\n请检查 API Key 与网络（https://api.deepseek.com），左侧本地匹配结果仍然可用。")
            self.set_status("AI 请求失败")

    def copy_ai_answer(self):
        text = self.ai_answer.get("1.0", "end-1c").strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.set_status("✅ 已复制 AI 回答")

    # ---------- 一键添加（从 AI 回答） ----------
    def add_from_ai(self):
        text = self.ai_answer.get("1.0", "end-1c").strip()
        if not text:
            self.set_status("没有 AI 回答内容，请先在问答页提问")
            return
        parsed = parse_ai_commands(text)
        if not parsed:
            self.set_status("AI 回答中未解析到 git 指令（需要 ``` 代码块格式）")
            return
        existing_cmds = {it.get("command", "").strip() for it in self.items}
        rows = []
        for p in parsed:
            cmd = p["command"]
            rows.append({
                "command": cmd,
                "note": p["note"],
                "category": guess_category(cmd),
                "exists": cmd in existing_cmds,
            })
        new_count = sum(1 for r in rows if not r["exists"])
        if new_count == 0:
            self.set_status("AI 回答中的指令本地都已存在，无需添加")
            return
        self._show_add_dialog(rows)

    def _show_add_dialog(self, rows):
        """预览对话框：勾选要添加的指令，可改分类/注释，支持多条"""
        dlg = tk.Toplevel(self.root)
        dlg.title("一键添加指令（来自 AI 回答）")
        dlg.configure(bg=COLORS["bg2"])
        dlg.geometry("820x520")
        dlg.transient(self.root)
        dlg.grab_set()

        # 顶部提示
        tk.Label(dlg, text="勾选要加入本地库的指令，可修改分类与注释：",
                 font=self.ui_font, fg=COLORS["dim"], bg=COLORS["bg2"],
                 anchor="w").pack(fill="x", padx=14, pady=(12, 6))

        # 滚动列表
        wrap = tk.Frame(dlg, bg=COLORS["bg2"])
        wrap.pack(fill="both", expand=True, padx=10)
        canvas = tk.Canvas(wrap, bg=COLORS["bg2"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        row_frame = tk.Frame(canvas, bg=COLORS["bg2"])
        win = canvas.create_window((0, 0), window=row_frame, anchor="nw")
        row_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        all_cats = all_categories(self.items)
        row_vars = []  # (command, check_var, cat_var, note_var)

        for r in rows:
            line = tk.Frame(row_frame, bg=COLORS["card"])
            line.pack(fill="x", padx=4, pady=3)

            check_var = tk.BooleanVar(value=not r["exists"])
            tk.Checkbutton(line, variable=check_var, bg=COLORS["card"],
                           activebackground=COLORS["card"], relief="flat",
                           cursor="hand2").pack(side="left", padx=(8, 2))

            cmd_label = tk.Label(line, text=r["command"], font=self.mono_font,
                                 fg=COLORS["text"], bg=COLORS["card"], anchor="w")
            cmd_label.pack(side="left", padx=(4, 6))
            if r["exists"]:
                tk.Label(line, text="（已存在）", font=("Microsoft YaHei UI", 9),
                         fg=COLORS["dim"], bg=COLORS["card"]).pack(side="left")

            cat_var = tk.StringVar(value=r["category"])
            cat_box = ttk.Combobox(line, textvariable=cat_var, values=all_cats,
                                   font=("Microsoft YaHei UI", 9), width=9)
            cat_box.pack(side="right", padx=6)

            note_var = tk.StringVar(value=r["note"])
            tk.Entry(line, textvariable=note_var, font=self.ui_font,
                     bg=COLORS["input_bg"], fg=COLORS["text"],
                     insertbackground=COLORS["text"], relief="flat").pack(
                side="right", fill="x", expand=True, padx=(6, 2))

            row_vars.append((r["command"], check_var, cat_var, note_var))

        # 底部按钮
        btn_row = tk.Frame(dlg, bg=COLORS["bg2"])
        btn_row.pack(fill="x", padx=14, pady=10)

        def update_count(*_a):
            n = sum(1 for _, v, _, _ in row_vars if v.get())
            btn_ok.config(text=f"添加选中 ({n}) 条")

        def confirm():
            added = 0
            for cmd, check_var, cat_var, note_var in row_vars:
                if not check_var.get():
                    continue
                cat = cat_var.get().strip() or "其他常用"
                note = note_var.get().strip()
                self.items.append({"category": cat, "command": cmd, "note": note})
                added += 1
            if added:
                self.current_cat = "全部"
                self._persist(f"已从 AI 回答添加 {added} 条指令")
            dlg.destroy()

        btn_ok = tk.Button(btn_row, text="添加选中 (0) 条", command=confirm,
                           font=self.ui_font, bg=COLORS["accent"], fg="#10101c",
                           activebackground=COLORS["accent_dim"], activeforeground="#ffffff",
                           relief="flat", padx=16, pady=4, cursor="hand2")
        btn_ok.pack(side="right")
        tk.Button(btn_row, text="取消", command=dlg.destroy, font=self.ui_font,
                  bg=COLORS["bg3"], fg=COLORS["dim"], relief="flat",
                  padx=14, pady=4, cursor="hand2").pack(side="right", padx=8)

        for _, v, _, _ in row_vars:
            v.trace_add("write", update_count)
        update_count()

    def _copy_fuzzy_selected(self, event=None):
        sel = self.fuzzy_list.curselection()
        if not sel:
            return
        line = self.fuzzy_list.get(sel[0])
        cmd = line.split("  ｜ ")[0]
        self.copy_command(cmd)

    # ---------- 动作 ----------
    def copy_command(self, cmd):
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        self.root.update()
        self.set_status(f"已复制：{cmd} ✓")

    def add_item(self):
        cat, cmd, note = self._ask_edit(None)
        if cat is None:
            return
        self.items.append({"category": cat, "command": cmd, "note": note})
        self.current_cat = cat
        self._persist("已添加命令")

    def edit_item(self, item):
        cat, cmd, note = self._ask_edit(item)
        if cat is None:
            return
        item["category"] = cat
        item["command"] = cmd
        item["note"] = note
        self.current_cat = cat
        self._persist("已保存修改")

    def delete_item(self, item):
        if not messagebox.askyesno("删除确认",
                                   f"确定删除这条命令吗？\n\n{item.get('command', '')}"):
            return
        self.items.remove(item)
        self._persist("已删除命令")

    def _persist(self, ok_msg):
        if not save_items(self.items):
            self.set_status("⚠️ 保存失败：数据文件不可写，请检查权限")
            return
        self.refresh()
        self.set_status(f"{ok_msg} · 共 {len(self.items)} 条")

    # ---------- 添加/编辑对话框 ----------
    def _ask_edit(self, item):
        """返回 (category, command, note)；取消返回 (None, None, None)"""
        dlg = tk.Toplevel(self.root)
        dlg.title("编辑命令" if item else "添加命令")
        dlg.configure(bg=COLORS["bg2"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        pad = {"padx": 16, "pady": 6}
        frm = tk.Frame(dlg, bg=COLORS["bg2"])
        frm.pack(fill="both", expand=True, **pad)

        def field_label(text):
            return tk.Label(frm, text=text, font=self.ui_font,
                            fg=COLORS["dim"], bg=COLORS["bg2"], anchor="w")

        def field_entry():
            return tk.Entry(frm, font=self.ui_font, bg=COLORS["input_bg"], fg=COLORS["text"],
                            insertbackground=COLORS["text"], relief="flat", width=48)

        # 分类（下拉 + 可输入新分类）
        field_label("分类").grid(row=0, column=0, sticky="w", pady=(4, 2))
        cats = all_categories(self.items)
        cat_var = tk.StringVar(value=(item.get("category", "") if item else (cats[0] if cats else "")))
        cat_box = ttk.Combobox(frm, textvariable=cat_var, values=cats,
                               font=self.ui_font, width=46)
        cat_box.grid(row=1, column=0, sticky="we", pady=(0, 6))

        # 命令
        field_label("命令（可含参数占位符）").grid(row=2, column=0, sticky="w", pady=(4, 2))
        cmd_var = tk.StringVar(value=item.get("command", "") if item else "")
        cmd_entry = field_entry()
        cmd_entry.configure(textvariable=cmd_var)
        cmd_entry.grid(row=3, column=0, sticky="we", pady=(0, 6))

        # 注释
        field_label("注释 / 说明").grid(row=4, column=0, sticky="w", pady=(4, 2))
        note_text = tk.Text(frm, font=self.ui_font, bg=COLORS["input_bg"], fg=COLORS["text"],
                            insertbackground=COLORS["text"], relief="flat",
                            height=4, width=48, wrap="word")
        if item:
            note_text.insert("1.0", item.get("note", ""))
        note_text.grid(row=5, column=0, sticky="we", pady=(0, 10))

        result = {}

        def ok():
            cat = cat_var.get().strip() or "未分类"
            cmd = cmd_var.get().strip()
            note = note_text.get("1.0", "end-1c").strip()
            if not cmd:
                messagebox.showwarning("提示", "命令不能为空", parent=dlg)
                return
            result["cat"], result["cmd"], result["note"] = cat, cmd, note
            dlg.destroy()

        def cancel():
            dlg.destroy()

        btns = tk.Frame(frm, bg=COLORS["bg2"])
        btns.grid(row=6, column=0, sticky="e")
        tk.Button(btns, text="取消", command=cancel, font=self.ui_font,
                  bg=COLORS["bg3"], fg=COLORS["dim"], relief="flat",
                  padx=14, pady=4, cursor="hand2").pack(side="left", padx=6)
        tk.Button(btns, text="保存", command=ok, font=self.ui_font,
                  bg=COLORS["accent"], fg="#10101c", relief="flat",
                  padx=16, pady=4, cursor="hand2").pack(side="left")

        dlg.bind("<Return>", lambda e: ok())
        dlg.bind("<Escape>", lambda e: cancel())
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dlg.winfo_height()) // 3
        dlg.geometry(f"+{x}+{y}")
        cmd_entry.focus_set()
        self.root.wait_window(dlg)
        return result.get("cat"), result.get("cmd"), result.get("note")

    def set_status(self, msg):
        self.status_label.config(text=msg)


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.2)  # 高分屏缩放
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

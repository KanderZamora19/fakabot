#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 授权检查 - 请勿删除此部分，否则程序无法运行
import _auth_check

# Consolidated utilities module: merged from utils/*.py
# Sections:
# - constants: STATUS_ZH, MSG
# - home: render_home
# - keyboards: build_payment_rows, row_back, row_home_admin, make_markup
# - misc: parse_date, fmt_ts, to_base36, bar
# - notify: notify_admin
# - sender: send_ephemeral
# - settings: ensure_settings_table, get_setting, set_setting

from __future__ import annotations

import asyncio
import datetime
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
except Exception:  # 测试环境兜底桩：不影响真实运行
    class InlineKeyboardButton:  # type: ignore
        def __init__(self, text: str, callback_data: Optional[str] = None):
            self.text = text
            self.callback_data = callback_data

    class InlineKeyboardMarkup:  # type: ignore
        def __init__(self, inline_keyboard):
            self.inline_keyboard = inline_keyboard

    class Bot:  # type: ignore
        async def send_message(self, chat_id: int, text: str, **kwargs):
            # 返回与 python-telegram-bot 类似的对象属性
            return SimpleNamespace(message_id=1, chat_id=chat_id, text=text)

        async def delete_message(self, chat_id: int, message_id: int):
            return None

__all__ = [
    # constants
    "STATUS_ZH",
    "MSG",
    # home
    "render_home",
    # keyboards
    "build_payment_rows",
    "row_back",
    "row_home_admin",
    "make_markup",
    # misc
    "parse_date",
    "fmt_ts",
    "to_base36",
    "bar",
    # notify
    "notify_admin",
    # sender
    "send_ephemeral",
    # settings
    "ensure_settings_table",
    "get_setting",
    "set_setting",
]

# ---------------- constants.py ----------------
# 统一的状态/文案常量
STATUS_ZH: Dict[str, str] = {
    "pending": "待支付",
    "paid": "已支付",
    "processing": "处理中",
    "completed": "已完成",
    "cancelled": "已取消",
    "expired": "已超时",
    "refunded": "已退款",
    "failed": "支付失败",
}

# 常用短句（可逐步接入以实现统一文案/i18n）
MSG: Dict[str, str] = {
    "saved_and_back": "✅ 已保存变更，返回商品页…",
    "created_and_back": "✅ 新商品已创建，返回列表…",
    "refreshing": "正在刷新…",
    "refreshed": "✅ 刷新完成",
}

# ---------------- home.py ----------------
# 类型注释仅作参考，不强制
_GetSetting = Callable[[str, Optional[str]], Optional[str]]

async def render_home(
    chat_id: int,
    cur,
    START_CFG,
    _get_setting: _GetSetting,
    _delete_last_and_send_photo: Callable[..., Any],
    _delete_last_and_send_text: Callable[..., Any],
    *,
    extra_rows: Optional[list[list[InlineKeyboardButton]]] = None,
):
    """渲染首页（封面 + 标题/简介 + 商品按钮）。
    所有依赖通过参数传入，方便在不同模块中复用。
    """
    try:
        title = (_get_setting("home.title", (START_CFG.get("title") or "欢迎选购")) or "欢迎选购").strip()
    except Exception:
        title = "欢迎选购"
    try:
        intro = (_get_setting("home.intro", (START_CFG.get("intro") or "请选择下方商品进行购买")) or "请选择下方商品进行购买").strip()
    except Exception:
        intro = "请选择下方商品进行购买"
    try:
        cover = _get_setting("home.cover_url", START_CFG.get("cover_url") or None)
    except Exception:
        cover = None

    try:
        rows: List[Tuple[int, str, float]] = cur.execute(
            "SELECT id, name, price FROM products WHERE status='on'"
        ).fetchall()
    except Exception:
        rows = []

    # 每行商品数：从 settings 读取，可选 1-4，默认 2
    try:
        cols_raw = _get_setting("home.products_per_row", (START_CFG.get("products_per_row") or 2))
        cols = int(cols_raw or 2)
    except Exception:
        cols = 2
    cols = max(1, min(4, cols))

    # 读取按钮文案模板。支持占位符：{name}、{price}
    try:
        btn_tpl = _get_setting("home.button_template", (START_CFG.get("button_template") or " {name} | ¥{price}")) or " {name} | ¥{price}"
    except Exception:
        btn_tpl = " {name} | ¥{price}"

    buttons: List[List[InlineKeyboardButton]] = []
    row_btn: List[InlineKeyboardButton] = []
    for pid, name, price in rows:
        try:
            label = str(btn_tpl).replace("{name}", str(name)).replace("{price}", str(price))
        except Exception:
            label = f" {name} | ¥{price}"
        row_btn.append(InlineKeyboardButton(label, callback_data=f"detail:{pid}"))
        if len(row_btn) >= cols:
            buttons.append(row_btn)
            row_btn = []
    if row_btn:
        buttons.append(row_btn)

    # 追加额外按钮行（例如：返回）
    if extra_rows:
        for r in extra_rows:
            if isinstance(r, list) and r:
                buttons.append(r)

    # 客服入口改为独立命令 /support，此处不再在首页展示按钮

    caption = f"{title}\n\n{intro}\n\n请选择商品："

    if cover:
        try:
            await _delete_last_and_send_photo(
                chat_id,
                cover,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
            )
            return
        except Exception:
            pass
    await _delete_last_and_send_text(
        chat_id,
        caption,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )

# ---------------- keyboards.py ----------------

def build_payment_rows(
    paycfg: Dict[str, dict],
    *,
    enabled_key: str = "enabled",
    priority_key: str = "priority",
    name_key: str = "name",
    callback_fmt: str = "pay:{channel}:{pid}",
    pid: Optional[str] = None,
    max_cols: int = 2,
    get_setting_func: Optional[Callable[[str, str], str]] = None,
    skip_single: bool = False,
) -> List[List[InlineKeyboardButton]]:
    """
    根据支付方式配置生成按钮行：
    - 过滤掉未启用项（enabled=False 或数据库设置为关闭）
    - 按 priority 从小到大排序（默认 100）
    - 每行最多 max_cols 个

    paycfg 示例：{
      "alipay": {"name": "支付宝", "enabled": true, "priority": 10},
      "wxpay": {"name": "微信", "enabled": false, "priority": 20},
    }
    """
    # 如果有get_setting_func，使用管理员设置的排序
    if get_setting_func:
        order_str = get_setting_func("payment.order", "alipay,wxpay,usdt_lemon,usdt_token188")
        payment_order = order_str.split(",")
        
        items: List[Tuple[int, str, str]] = []
        for i, ch in enumerate(payment_order):
            if ch not in paycfg:
                continue
            cfg = paycfg[ch]
            
            # 检查配置文件中的enabled
            if not cfg.get(enabled_key, True):
                continue
            
            # 检查数据库中的开关设置（管理员可控制）
            db_enabled = get_setting_func(f"payment.{ch}.enabled", "true") == "true"
            if not db_enabled:
                continue
            
            label = str(cfg.get(name_key) or ch)
            items.append((i, ch, label))  # 使用顺序索引而不是priority
    else:
        # 回退到原来的priority排序
        items: List[Tuple[int, str, str]] = []
        for ch, cfg in paycfg.items():
            # 检查配置文件中的enabled
            if not cfg.get(enabled_key, True):
                continue
            
            pri = int(cfg.get(priority_key, 100) or 100)
            label = str(cfg.get(name_key) or ch)
            items.append((pri, ch, label))
        items.sort(key=lambda x: x[0])

    # 如果启用skip_single且只有一个支付方式，返回空列表
    if skip_single and len(items) == 1:
        return []
    
    rows_kb: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for _, channel, label in items:
        cb = callback_fmt.format(channel=channel, pid=pid or "")
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) >= max_cols:
            rows_kb.append(row)
            row = []
    if row:
        rows_kb.append(row)
    return rows_kb


def get_first_enabled_payment(
    paycfg: Dict[str, dict],
    *,
    enabled_key: str = "enabled",
    get_setting_func: Optional[Callable[[str, str], str]] = None,
) -> Optional[str]:
    """
    获取第一个启用的支付方式
    """
    # 如果有get_setting_func，使用管理员设置的排序
    if get_setting_func:
        order_str = get_setting_func("payment.order", "alipay,wxpay,usdt_lemon,usdt_token188")
        payment_order = order_str.split(",")
        
        for ch in payment_order:
            if ch not in paycfg:
                continue
            cfg = paycfg[ch]
            
            # 检查配置文件中的enabled
            if not cfg.get(enabled_key, True):
                continue
            
            # 检查数据库中的开关设置（管理员可控制）
            db_enabled = get_setting_func(f"payment.{ch}.enabled", "true") == "true"
            if not db_enabled:
                continue
            
            return ch
    else:
        # 回退到原来的priority排序
        items = []
        for ch, cfg in paycfg.items():
            # 检查配置文件中的enabled
            if not cfg.get(enabled_key, True):
                continue
            
            pri = int(cfg.get("priority", 100) or 100)
            items.append((pri, ch))
        items.sort(key=lambda x: x[0])
        
        if items:
            return items[0][1]
    
    return None


def row_back(callback_data: str, label: str = "⬅️ 返回") -> List[InlineKeyboardButton]:
    return [InlineKeyboardButton(label, callback_data=callback_data)]


def row_home_admin(label: str = "🏠 返回面板") -> List[InlineKeyboardButton]:
    return [InlineKeyboardButton(label, callback_data="adm:menu")]


def make_markup(rows: Sequence[Sequence[InlineKeyboardButton]] | None) -> Optional[InlineKeyboardMarkup]:
    if not rows:
        return None
    return InlineKeyboardMarkup(list(rows))

# 统一的付款台控制行：用于“重新检查/取消付款”等
def rows_pay_console(otn: str) -> List[List[InlineKeyboardButton]]:
    return [[
        InlineKeyboardButton("🔄 我已支付，重新检查", callback_data=f"recheck:{otn}"),
        InlineKeyboardButton("❌ 取消本次付款", callback_data=f"ask:cancel:{otn}"),
    ]]

# 通用确认对话行：yes/no 两个按钮在同一行
def build_confirm_rows(yes_cb: str, no_cb: str, yes_label: str = "✅ 确定", no_label: str = "↩️ 返回") -> List[List[InlineKeyboardButton]]:
    return [[
        InlineKeyboardButton(yes_label, callback_data=yes_cb),
        InlineKeyboardButton(no_label, callback_data=no_cb),
    ]]

# ---------------- misc.py ----------------

def parse_date(s: str):
    """Parse YYYY-MM-DD to unix timestamp (seconds). Return None on failure/empty."""
    try:
        s = (s or "").strip()
        if not s:
            return None
        y, m, d = s.split("-")
        tm = time.strptime(f"{int(y):04d}-{int(m):02d}-{int(d):02d}", "%Y-%m-%d")
        return int(time.mktime(tm))
    except Exception:
        return None


def fmt_ts(ts: int) -> str:
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(ts or 0)))
    except Exception:
        return "-"


def to_base36(n: int) -> str:
    """Encode non-negative int to uppercase base36 string."""
    try:
        x = int(n)
        if x < 0:
            x = -x
        if x == 0:
            return "0"
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        s: List[str] = []
        while x > 0:
            x, r = divmod(x, 36)
            s.append(chars[r])
        return "".join(reversed(s))
    except Exception:
        return str(n)


def bar(val: float, maxv: float, width: int = 20) -> str:
    if maxv <= 0:
        return ""
    n = int(round((float(val) / float(maxv)) * width))
    n = max(0, min(width, n))
    return "█" * n + "·" * (width - n)

# ---------------- notify.py ----------------

async def notify_admin(
    bot: Bot,
    text: str,
    admin_id: int,
    *,
    prefix: str = "[通知]",
    attach_time: bool = True,
    context: Optional[str] = None,
) -> None:
    """
    统一的管理员通知工具。

    参数:
    - bot: Telegram Bot 实例
    - text: 主体文本
    - admin_id: 管理员聊天ID（从配置读取并传入）
    - prefix: 前缀标签，如 "[错误]"、"[告警]"、"[通知]"
    - attach_time: 是否追加时间戳
    - context: 可选上下文信息，追加到消息末尾
    """
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if attach_time else None
        parts: List[str] = []
        if prefix:
            parts.append(prefix)
        parts.append(text.strip())
        if context:
            parts.append(str(context).strip())
        if ts:
            parts.append(f"@{ts}")
        msg = " ".join(part for part in parts if part)
        await bot.send_message(admin_id, text=msg)
    except Exception:
        # 通知失败不影响主流程
        pass

# ---------------- sender.py ----------------

async def send_ephemeral(bot: Bot, chat_id: int, text: str, ttl: int = 5) -> Optional[int]:
    """
    发送一条会在 ttl 秒后自动删除的临时文本消息。

    :param bot: telegram.Bot 实例
    :param chat_id: 目标聊天 ID
    :param text: 文本内容
    :param ttl: 存活时间（秒），默认 5
    :return: 已发送消息的 message_id（若发送失败则返回 None）
    """
    msg = None
    try:
        msg = await bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        return None

    async def _del_later(c_id: int, m_id: int, delay: int):
        try:
            await asyncio.sleep(max(1, int(delay)))
            await bot.delete_message(chat_id=c_id, message_id=m_id)
        except Exception:
            pass

    try:
        asyncio.create_task(_del_later(msg.chat_id, msg.message_id, ttl))
    except Exception:
        pass
    return getattr(msg, "message_id", None)

# ---------------- settings.py ----------------

def ensure_settings_table(cur, conn) -> None:
    try:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS settings(\n"
            "  key TEXT PRIMARY KEY,\n"
            "  value TEXT\n"
            ")"
        )
        conn.commit()
    except Exception:
        pass


def get_setting(cur, key: str, default: Optional[str] = "") -> Optional[str]:
    try:
        row = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row and row[0] is not None:
            return str(row[0])
    except Exception:
        pass
    return default


def set_setting(cur, conn, key: str, value: str) -> None:
    try:
        cur.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    except Exception:
        pass


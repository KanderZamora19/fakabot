#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 授权检查 - 请勿删除此部分，否则程序无法运行
import _auth_check

from __future__ import annotations
import asyncio
import json
import time
import io
from typing import Callable, Any, Dict

from telegram import Update, InlineKeyboardButton
from utils import send_ephemeral
from utils import row_back, row_home_admin, make_markup
from utils import STATUS_ZH
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application
from utils import render_home
from utils import parse_date as _parse_date, fmt_ts as _fmt_ts, to_base36 as _to_base36, bar as _bar

# 该模块通过依赖注入方式复用主程序的资源，避免循环依赖
# 使用方式：在 bot.py 中调用 register_admin_handlers(application, deps)
# deps 包含：
#   - is_admin: Callable[[int], bool]
#   - cur, conn: sqlite cursor/connection
#   - CFG_PATH: str
#   - START_CFG: dict (引用)
#   - sync_products_from_config: Callable[[list], None] (可选)
#   - _delete_last_and_send_text, _delete_last_and_send_photo: 发送工具


def register_admin_handlers(app: Application, deps: Dict[str, Any]):
    is_admin: Callable[[int], bool] = deps["is_admin"]
    cur = deps["cur"]
    conn = deps["conn"]
    CFG_PATH: str = deps["CFG_PATH"]
    START_CFG: dict = deps["START_CFG"]
    _send_text = deps["_delete_last_and_send_text"]
    _send_photo = deps["_delete_last_and_send_photo"]
    mark_paid_and_send_invite = deps.get("mark_paid_and_send_invite")
    _get_setting = deps.get("_get_setting")
    _set_setting = deps.get("_set_setting")

    # ---------- helpers ----------
    async def _guard_admin(update: Update) -> bool:
        uid = update.effective_user.id
        if not is_admin(uid):
            try:
                # 采用一次性提示，并在数秒后自动删除
                await send_ephemeral(
                    update.get_bot(),
                    update.effective_chat.id,
                    "✨ 嗨～这里是官方店后台，您不是管理员呢，无法为您展示😯～",
                    ttl=5,
                )
            except Exception:
                pass
            return False
        return True

    # settings 表读写由主程序注入；此处不再重复创建表，保持轻量。

    # ---------- date/misc helpers ----------
    # 复用 utils.misc 中的通用实现（已通过别名导入同名变量）

    # 确保 products 表具备 sort 列（防止主程序未先运行迁移时，商品管理点开无响应）
    def _ensure_product_sort_column():
        try:
            # 简单探测列是否存在
            cur.execute("SELECT sort FROM products LIMIT 1")
            _ = cur.fetchone()
            return
        except Exception:
            pass
        # 列不存在则尝试添加并回填
        try:
            cur.execute("ALTER TABLE products ADD COLUMN sort INTEGER")
            conn.commit()
        except Exception:
            pass
        try:
            cur.execute("UPDATE products SET sort = id WHERE sort IS NULL")
            conn.commit()
        except Exception:
            pass

    async def _admin_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _guard_admin(update):
            return
        kb = make_markup([
            [InlineKeyboardButton("📦 商品管理", callback_data="adm:plist:1"), InlineKeyboardButton("🖼️ 主页编辑", callback_data="adm:home")],
            [InlineKeyboardButton("📑 订单管理", callback_data="adm:olist:1:all"), InlineKeyboardButton("📊 统计报表", callback_data="adm:ostat")],
            [InlineKeyboardButton("💳 支付设置", callback_data="adm:pay"), InlineKeyboardButton("📢 公告设置", callback_data="adm:announcement")],
            [InlineKeyboardButton("🆘 客服设置", callback_data="adm:support")],
            [InlineKeyboardButton("🧹 优化数据库", callback_data="adm:vacuum")],
        ])
        await _send_text(update.effective_chat.id, "🔧 管理面板：请选择功能", reply_markup=kb)

    async def _send_home_menu(chat_id: int):
        cur_cols = (_get_setting("home.products_per_row", str(START_CFG.get("products_per_row") or "2")) or "2").strip()
        cur_tpl = (_get_setting("home.button_template", (START_CFG.get("button_template") or " {name} | ¥{price}")) or " {name} | ¥{price}")
        # 简短描述
        def _tpl_desc(t: str) -> str:
            t = str(t)
            if "{name}" in t and "{price}" in t:
                # 判断常见两种
                if "|" in t:
                    return "名称 | 价格"
                if "-" in t:
                    return "价格 - 名称"
                return "名称+价格"
            if "{name}" in t and "{price}" not in t:
                return "仅名称"
            if "{price}" in t and "{name}" not in t:
                return "仅价格"
            return "自定义"
        cur_tpl_desc = _tpl_desc(cur_tpl)
        kb = make_markup([
            [InlineKeyboardButton("✏️ 改标题", callback_data="adm:home_title"), InlineKeyboardButton("📝 改简介", callback_data="adm:home_intro")],
            [InlineKeyboardButton("🖼️ 改封面链接", callback_data="adm:home_cover"), InlineKeyboardButton("👀 预览主页", callback_data="adm:home_preview")],
            [InlineKeyboardButton(f"🏷️ 按钮文案：{cur_tpl_desc}", callback_data="adm:home_btntpl"), InlineKeyboardButton(f"🧩 每行商品数：{cur_cols}", callback_data="adm:home_cols")],
            row_home_admin(),
        ])
        cur_title = (_get_setting("home.title", (START_CFG.get("title") or "")).strip())
        cur_intro = (_get_setting("home.intro", (START_CFG.get("intro") or "")).strip())
        cur_cover = (_get_setting("home.cover_url", (START_CFG.get("cover_url") or "")).strip())
        text = (
            f"主页设置\n"
            f"标题：{cur_title or '-'}\n"
            f"简介：{(cur_intro or '-')[:200]}\n"
            f"封面：{cur_cover or '-'}\n"
            f"每行商品数：{cur_cols} (1-4)\n"
            f"按钮文案：{cur_tpl_desc}"
        )
        await _send_text(chat_id, text, reply_markup=kb)

    async def _send_home_preview(chat_id: int):
        # 复用通用首页渲染，并在末尾追加“返回”按钮
        await render_home(
            chat_id,
            cur,
            START_CFG,
            _get_setting,
            _send_photo,
            _send_text,
            extra_rows=[row_back("adm:home")],
        )

    async def _send_product_page(chat_id: int, pid: str):
        row = cur.execute("SELECT id, name, price, full_description, cover_url, COALESCE(status,'on'), COALESCE(deliver_type,'join_group'), COALESCE(card_fixed,'') FROM products WHERE id=?", (pid,)).fetchone()
        if not row:
            kb = make_markup([
                row_back("adm:plist:1"),
                row_home_admin(),
            ])
            await _send_text(chat_id, "⚠️ 未找到该商品", reply_markup=kb)
            return
        _pid, name, price, desc, cover, status, deliver_type, card_fixed_val = row
        # 统计卡池余量
        try:
            stock_row = cur.execute("SELECT COUNT(*) FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL", (_pid,)).fetchone()
            stock_cnt = int(stock_row[0] or 0)
        except Exception:
            stock_cnt = 0
        kb = make_markup([
            [InlineKeyboardButton("✏️ 改名称", callback_data=f"adm:edit_name:{_pid}"), InlineKeyboardButton("💰 改价格", callback_data=f"adm:edit_price:{_pid}")],
            [InlineKeyboardButton("📝 改详情", callback_data=f"adm:edit_desc:{_pid}"), InlineKeyboardButton("🖼️ 改封面", callback_data=f"adm:edit_cover:{_pid}")],
            [InlineKeyboardButton("🚚 发货方式", callback_data=f"adm:edit_deliver:{_pid}"), InlineKeyboardButton("🧷 通用卡密", callback_data=f"adm:edit_card_fixed:{_pid}")],
            [InlineKeyboardButton("🔑 卡密库存", callback_data=f"adm:card_pool:{_pid}:1"), InlineKeyboardButton("👥 改群ID", callback_data=f"adm:edit_group:{_pid}")],
            [InlineKeyboardButton("⏯ 上/下架", callback_data=f"adm:toggle:{_pid}"), InlineKeyboardButton("🗑️ 删除", callback_data=f"adm:del:{_pid}")],
            row_back("adm:plist:1"),
        ])
        # 本地化发货方式
        _deliver_label = {"join_group": "自动拉群", "card_fixed": "通用卡密", "card_pool": "卡池"}.get(str(deliver_type or ""), str(deliver_type or "-"))
        text = (
            f"商品 #{_pid}\n"
            f"名称：{name}\n"
            f"价格：¥{price}\n"
            f"状态：{'上架' if (status or 'on')=='on' else '下架'}\n"
            f"封面：{cover or '-'}\n"
            f"发货方式：{_deliver_label}\n"
            f"卡池余量：{stock_cnt}\n"
            f"详情：{(desc or '-')[:300]}"
        )
        if cover:
            try:
                await _send_photo(chat_id, cover, caption=text, reply_markup=kb)
                return
            except Exception:
                pass
        await _send_text(chat_id, text, reply_markup=kb)

    # ---------- direct render helpers ----------
    def _build_order_status_row(status_key: str):
        # 合并“已支付+已完成”为“已成交(done)”
        filters = [
            ("全部", "all"),
            ("待支付", "pending"),
            ("已成交", "done"),
            ("已取消", "cancelled"),
        ]
        frow = []
        for label, key in filters:
            prefix = "✅ " if key == status_key else ""
            frow.append(InlineKeyboardButton(f"{prefix}{label}", callback_data=f"adm:olist:1:{key}"))
        return frow

    def _build_order_pagination(page: int, total_pages: int, status_key: str):
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"adm:olist:{page-1}:{status_key}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"adm:olist:{page+1}:{status_key}"))
        return nav

    def _build_order_toolbar(status_key: str, page: int, qkw: str, start_ts: int | None, end_ts: int | None):
        # 同一行放置：时间范围 | 搜索
        return [[
            InlineKeyboardButton("⏱️ 设置时间范围", callback_data=f"adm:of_setrange:{status_key}:{page}"),
            InlineKeyboardButton("🔎 搜索", callback_data=f"adm:of_search:{status_key}:{page}"),
        ]]

    def _build_stat_toolbar():
        # 统计快捷范围：仅保留 今日/本月/本年
        return [
            [InlineKeyboardButton("📅 今日", callback_data="adm:sf_today"), InlineKeyboardButton("📅 本月", callback_data="adm:sf_month"), InlineKeyboardButton("📅 本年", callback_data="adm:sf_year")],
            row_home_admin(),
        ]
    async def _send_order_list(chat_id: int, page: int, status_key: str, ctx: ContextTypes.DEFAULT_TYPE):
        page_size = 10
        ofilter = ctx.user_data.get("adm_ofilter", {})
        start_ts = ofilter.get("start_ts")
        end_ts = ofilter.get("end_ts")
        osearch = ctx.user_data.get("adm_osearch", {})
        qkw = (osearch.get("q") or "").strip()
        where = []
        params = []
        # 状态筛选：all 不限制；done = paid 或 completed
        if status_key and status_key != "all":
            if status_key == "done":
                where.append("o.status IN ('paid','completed')")
            else:
                where.append("o.status=?")
                params.append(status_key)
        if start_ts:
            where.append("o.create_time>=?")
            params.append(int(start_ts))
        if end_ts:
            where.append("o.create_time<=?")
            params.append(int(end_ts))
        if qkw:
            or_clauses = [
                "CAST(o.user_id AS TEXT)=?",
                "CAST(o.product_id AS TEXT)=?",
                "p.name LIKE ?",
                "o.out_trade_no LIKE ?",
            ]
            where.append("(" + " OR ".join(or_clauses) + ")")
            params.extend([qkw, qkw, f"%{qkw}%", f"%{qkw}%"])
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        # 先计算总数/总页数，再夹紧页码，避免空页
        # 注意：当搜索包含商品名条件（p.name）时，统计也需要 JOIN products
        total = cur.execute(
            f"SELECT COUNT(*) FROM orders o LEFT JOIN products p ON p.id=o.product_id {where_sql}",
            (*params,),
        ).fetchone()[0]
        total_pages = max(1, (total + page_size - 1) // page_size)
        # 夹紧页码
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * page_size
        rows = cur.execute(
            f"SELECT o.id, o.user_id, o.product_id, o.amount, o.payment_method, COALESCE(o.status,'pending'), o.create_time, o.out_trade_no, p.name "
            f"FROM orders o LEFT JOIN products p ON p.id=o.product_id {where_sql} "
            f"ORDER BY o.id DESC LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        ).fetchall()

        buttons = []
        for oid, uid, pid, amount, pm, st, cts, out_trade_no, pname in rows:
            # 显示为商户单号(out_trade_no)最后一段的“纯数字优先”后缀（如 MJ6K3A-89899 => 89899）。
            # 若该段无数字，则显示该段原样；再兜底 Base36(id)。
            try:
                part = (out_trade_no or "").split("-")[-1]
                digits = "".join(ch for ch in part if ch.isdigit()) if part else ""
                suffix = digits or part or _to_base36(oid)
            except Exception:
                suffix = _to_base36(oid)
            title = f"#{suffix}"
            buttons.append([
                InlineKeyboardButton(title, callback_data=f"adm:o:{oid}:{status_key}:{page}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"adm:odelc:{oid}:{status_key}:{page}")
            ])
        # 筛选状态按钮行
        frow = _build_order_status_row(status_key)
        if frow:
            buttons.append(frow)
        # 分页按钮行
        nav = _build_order_pagination(page, total_pages, status_key)
        if nav:
            buttons.append(nav)

        # 时间范围显示与设置
        sr_text = "未设置"
        if start_ts or end_ts:
            s = time.strftime('%Y-%m-%d', time.localtime(int(start_ts))) if start_ts else "-"
            e = time.strftime('%Y-%m-%d', time.localtime(int(end_ts))) if end_ts else "-"
            sr_text = f"{s} ~ {e}"
        # 搜索与工具区
        q_text = qkw if qkw else "(无)"
        for row_btns in _build_order_toolbar(status_key, page, qkw, start_ts, end_ts):
            buttons.append(row_btns)
        buttons.append(row_home_admin())

        # 展示中文状态文案
        label_map = {"all": "全部", "pending": "待支付", "done": "已成交", "cancelled": "已取消"}
        show_status = label_map.get(status_key, status_key)
        await _send_text(chat_id, f"📑 订单列表（第 {page}/{total_pages} 页）\n状态：{show_status}\n时间：{sr_text}\n搜索：{q_text}", reply_markup=make_markup(buttons))
        return

    async def _send_stat_page(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
        sfilter = ctx.user_data.get("adm_sfilter", {})
        start_ts = sfilter.get("start_ts")
        end_ts = sfilter.get("end_ts")
        where = []
        params = []
        if start_ts:
            where.append("o.create_time>=?")
            params.append(int(start_ts))
        if end_ts:
            where.append("o.create_time<=?")
            params.append(int(end_ts))
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        where_paid_sql = where_sql + ((" AND " if where else " WHERE ") + "o.status IN ('paid','completed')")

        row_all = cur.execute(f"SELECT COUNT(*) FROM orders o {where_sql}", (*params,)).fetchone()
        row_paid = cur.execute(
            f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders o {where_paid_sql}",
            (*params,)
        ).fetchone()
        o_all = int(row_all[0] or 0)
        o_paid = int(row_paid[0] or 0)
        amt_paid = float(row_paid[1] or 0.0)
        conv_rate = (o_paid / o_all * 100) if o_all > 0 else 0.0

        TOPN = 5
        base_where = ("WHERE " + " AND ".join(where) + (" AND " if where else "") + "o.status IN ('paid','completed')") if where else "WHERE o.status IN ('paid','completed')"
        prod_rows = cur.execute(
            "SELECT COALESCE(p.name,'商品') AS name, COUNT(o.id) AS cnt, COALESCE(SUM(o.amount),0) AS amt "
            "FROM orders o LEFT JOIN products p ON p.id=o.product_id "
            + base_where +
            " GROUP BY o.product_id ORDER BY amt DESC LIMIT ?",
            (*params, TOPN)
        ).fetchall()
        max_amt = max([float(r[2] or 0) for r in prod_rows] + [0])
        lines = []
        for name, cnt, amt in prod_rows:
            bar = _bar(float(amt or 0), max_amt, 20)
            lines.append(f"{name[:12]:<12} ¥{float(amt or 0):>8.2f} | {bar} ({int(cnt)}单)")

        sr_text = "未设置"
        if start_ts or end_ts:
            s = time.strftime('%Y-%m-%d', time.localtime(int(start_ts))) if start_ts else "-"
            e = time.strftime('%Y-%m-%d', time.localtime(int(end_ts))) if end_ts else "-"
            sr_text = f"{s} ~ {e}"

        text = (
            "📊 统计概览\n"
            f"时间范围：{sr_text}\n"
            f"成交订单：{o_paid} 单，金额 ¥{amt_paid:.2f}\n"
            f"下单/成交：{o_all}/{o_paid}，转化率：{conv_rate:.1f}%\n"
            "\n🏆 Top 商品（按金额）\n" + ("\n".join(lines) if lines else "(暂无数据)")
        )
        kb = make_markup(_build_stat_toolbar())
        await _send_text(chat_id, text, reply_markup=kb)

    async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await _admin_menu(update, ctx)

    async def adm_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _guard_admin(update):
            return
        q = update.callback_query
        # 一些操作（如清除筛选/搜索/统计筛选）会在同一回调中“伪路由”到其它分支，
        # 可能导致对同一个 callback_query 重复 answer，从而抛出异常并中断刷新。
        # 这里做兼容，忽略重复 answer 的异常，保证后续渲染继续执行。
        try:
            await q.answer()
        except Exception:
            pass
        data = q.data  # adm:...
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        # 清理等待态，避免串台（除编辑步骤继续输入场景外）
        # 仅在进入新页面时清理
        if action in {"plist", "p", "home", "pnew", "menu", "olist", "o", "ostat", "of_setrange", "of_search", "sf_today", "sf_month", "sf_year"}:
            ctx.user_data.pop("adm_wait", None)

        # 商品列表（分页 + 行内排序 上/下）
        if action == "plist":
            page = int(parts[2]) if len(parts) > 2 else 1
            page_size = 10
            offset = (page - 1) * page_size
            # 防御性迁移：确保存在 sort 列并已回填
            _ensure_product_sort_column()
            rows = cur.execute(
                "SELECT id, name, price, COALESCE(status,'on'), COALESCE(sort, id) AS s FROM products ORDER BY s DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            total = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            total_pages = max(1, (total + page_size - 1) // page_size)

            buttons = []
            row_btns = []
            for pid, name, price, status, _ in rows:
                # 每行两个，不显示价格
                row_btns.append(InlineKeyboardButton(f"{pid} {name}", callback_data=f"adm:p:{pid}"))
                if len(row_btns) >= 2:
                    buttons.append(row_btns)
                    row_btns = []
            if row_btns:
                buttons.append(row_btns)
            # 底部操作区：一行两个（排序本页 | 新增商品）
            buttons.append([
                InlineKeyboardButton("✏️ 排序本页", callback_data=f"adm:psort:{page}"),
                InlineKeyboardButton("➕ 新增商品", callback_data="adm:pnew"),
            ])
            # 分页导航
            nav = []
            if page > 1:
                nav.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"adm:plist:{page-1}"))
            if page < total_pages:
                nav.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"adm:plist:{page+1}"))
            if nav:
                buttons.append(nav)
            buttons.append(row_home_admin())
            await _send_text(update.effective_chat.id, f"📦 商品列表（第 {page}/{total_pages} 页）\n当前排序：自定义", reply_markup=make_markup(buttons))
            return

        # 首页：每行商品数设置入口
        if action == "home_cols":
            kb = make_markup([
                [InlineKeyboardButton("1", callback_data="adm:home_cols_set:1"), InlineKeyboardButton("2", callback_data="adm:home_cols_set:2"), InlineKeyboardButton("3", callback_data="adm:home_cols_set:3"), InlineKeyboardButton("4", callback_data="adm:home_cols_set:4")],
                row_back("adm:home"),
            ])
            await _send_text(update.effective_chat.id, "请选择每行商品数量（1-4）：", reply_markup=kb)
            return

        # 首页：保存每行商品数
        if action == "home_cols_set":
            val = parts[2] if len(parts) > 2 else "2"
            try:
                n = max(1, min(4, int(val)))
            except Exception:
                n = 2
            _set_setting("home.products_per_row", str(n))
            await _send_text(update.effective_chat.id, f"已设置每行商品数为：{n}", reply_markup=make_markup([row_back("adm:home")]))
            return

        # 支付设置主页
        if action == "pay":
            cur_cols = (_get_setting("ui.payment_cols", str(START_CFG.get("payment_cols") or "3")) or "3").strip()
            
            # 获取支付方式开关状态
            def get_payment_status(channel):
                return _get_setting(f"payment.{channel}.enabled", "true") == "true"
            
            # 构建支付方式开关按钮
            payment_buttons = []
            
            # 获取支付方式排序
            def get_payment_order():
                order_str = _get_setting("payment.order", "alipay,wxpay,usdt_lemon,usdt_token188")
                return order_str.split(",")
            
            def get_payment_name(channel):
                names = {
                    "alipay": "支付宝",
                    "wxpay": "微信", 
                    "usdt_lemon": "USDT (柠檬)",
                    "usdt_token188": "USDT(TRC20)"
                }
                return names.get(channel, channel)
            
            # 按照保存的顺序显示支付方式
            payment_order = get_payment_order()
            
            for i, channel in enumerate(payment_order):
                if channel not in ["alipay", "wxpay", "usdt_lemon", "usdt_token188"]:
                    continue
                    
                name = get_payment_name(channel)
                enabled = get_payment_status(channel)
                status_icon = "✅" if enabled else "❌"
                
                # 构建按钮行：开关 + 上移 + 下移
                row = [
                    InlineKeyboardButton(
                        f"{status_icon} {name}", 
                        callback_data=f"adm:pay_toggle:{channel}"
                    )
                ]
                
                # 添加上移按钮（不是第一个）
                if i > 0:
                    row.append(InlineKeyboardButton("⬆️", callback_data=f"adm:pay_up:{channel}"))
                else:
                    row.append(InlineKeyboardButton("　", callback_data="adm:noop"))  # 占位
                
                # 添加下移按钮（不是最后一个）
                if i < len(payment_order) - 1:
                    row.append(InlineKeyboardButton("⬇️", callback_data=f"adm:pay_down:{channel}"))
                else:
                    row.append(InlineKeyboardButton("　", callback_data="adm:noop"))  # 占位
                
                payment_buttons.append(row)
            
            kb = make_markup([
                [InlineKeyboardButton(f"🧩 每行支付按钮：{cur_cols}", callback_data="adm:pay_cols")],
                *payment_buttons,
                row_home_admin(),
            ])
            text = (
                "💳 支付设置\n"
                f"每行按钮数：{cur_cols} (1-4)\n"
                "\n📋 支付方式管理：\n"
                "• 点击支付方式名称：开启/关闭\n"
                "• 点击 ⬆️ ⬇️：调整显示顺序"
            )
            await _send_text(update.effective_chat.id, text, reply_markup=kb)
            return

        # 支付设置：选择每行按钮数
        if action == "pay_cols":
            kb = make_markup([
                [InlineKeyboardButton("1", callback_data="adm:pay_cols_set:1"), InlineKeyboardButton("2", callback_data="adm:pay_cols_set:2"), InlineKeyboardButton("3", callback_data="adm:pay_cols_set:3"), InlineKeyboardButton("4", callback_data="adm:pay_cols_set:4")],
                row_back("adm:pay"),
            ])
            await _send_text(update.effective_chat.id, "请选择每行支付按钮数量（1-4）：", reply_markup=kb)
            return

        # 支付设置：切换支付方式开关
        if action == "pay_toggle":
            channel = parts[2] if len(parts) > 2 else ""
            if channel:
                # 获取当前状态
                current_status = _get_setting(f"payment.{channel}.enabled", "true") == "true"
                # 切换状态
                new_status = "false" if current_status else "true"
                _set_setting(f"payment.{channel}.enabled", new_status)
                
                # 获取支付方式名称
                try:
                    with open(CFG_PATH, "r", encoding="utf-8") as f:
                        cfg_content = _strip_json_comments(f.read())
                        cfg = json.loads(cfg_content)
                        payments = cfg.get("PAYMENTS", {})
                        name = payments.get(channel, {}).get("name", channel)
                except Exception:
                    name = channel
                
                status_text = "开启" if new_status == "true" else "关闭"
                await send_ephemeral(
                    update.get_bot(), 
                    update.effective_chat.id, 
                    f"✅ {name} 已{status_text}", 
                    ttl=2
                )
            
            # 刷新支付设置页面
            await adm_router(type("obj", (), {
                "callback_query": type("q", (), {"data": "adm:pay"}), 
                "effective_user": update.effective_user, 
                "effective_chat": update.effective_chat, 
                "get_bot": update.get_bot
            })(), ctx)
            return

        # 支付方式上移
        if action == "pay_up":
            channel = parts[2] if len(parts) > 2 else ""
            if channel:
                # 获取当前排序
                order_str = _get_setting("payment.order", "alipay,wxpay,usdt_lemon,usdt_token188")
                order_list = order_str.split(",")
                
                # 找到当前位置并上移
                if channel in order_list:
                    current_index = order_list.index(channel)
                    if current_index > 0:
                        # 交换位置
                        order_list[current_index], order_list[current_index - 1] = order_list[current_index - 1], order_list[current_index]
                        # 保存新排序
                        new_order = ",".join(order_list)
                        _set_setting("payment.order", new_order)
                        
                        await send_ephemeral(
                            update.get_bot(), 
                            update.effective_chat.id, 
                            f"✅ 已上移", 
                            ttl=1
                        )
            
            # 刷新页面
            await adm_router(type("obj", (), {
                "callback_query": type("q", (), {"data": "adm:pay"}), 
                "effective_user": update.effective_user, 
                "effective_chat": update.effective_chat, 
                "get_bot": update.get_bot
            })(), ctx)
            return

        # 支付方式下移
        if action == "pay_down":
            channel = parts[2] if len(parts) > 2 else ""
            if channel:
                # 获取当前排序
                order_str = _get_setting("payment.order", "alipay,wxpay,usdt_lemon,usdt_token188")
                order_list = order_str.split(",")
                
                # 找到当前位置并下移
                if channel in order_list:
                    current_index = order_list.index(channel)
                    if current_index < len(order_list) - 1:
                        # 交换位置
                        order_list[current_index], order_list[current_index + 1] = order_list[current_index + 1], order_list[current_index]
                        # 保存新排序
                        new_order = ",".join(order_list)
                        _set_setting("payment.order", new_order)
                        
                        await send_ephemeral(
                            update.get_bot(), 
                            update.effective_chat.id, 
                            f"✅ 已下移", 
                            ttl=1
                        )
            
            # 刷新页面
            await adm_router(type("obj", (), {
                "callback_query": type("q", (), {"data": "adm:pay"}), 
                "effective_user": update.effective_user, 
                "effective_chat": update.effective_chat, 
                "get_bot": update.get_bot
            })(), ctx)
            return

        # 空操作（占位按钮）
        if action == "noop":
            await query.answer()
            return

        # 支付设置：保存每行按钮数
        if action == "pay_cols_set":
            val = parts[2] if len(parts) > 2 else "3"
            try:
                n = max(1, min(4, int(val)))
            except Exception:
                n = 3
            _set_setting("ui.payment_cols", str(n))
            await _send_text(update.effective_chat.id, f"已设置每行支付按钮数为：{n}", reply_markup=make_markup([row_back("adm:pay")]))
            return

        # 首页：按钮文案模板设置入口
        if action == "home_btntpl":
            kb = make_markup([
                [InlineKeyboardButton("名称 | 价格", callback_data="adm:home_btntpl_set:n_p"), InlineKeyboardButton("价格 - 名称", callback_data="adm:home_btntpl_set:p_n")],
                [InlineKeyboardButton("仅名称(隐藏价格)", callback_data="adm:home_btntpl_set:n_only")],
                row_back("adm:home"),
            ])
            await _send_text(update.effective_chat.id, "请选择按钮文案模板：", reply_markup=kb)
            return

        # 首页：保存按钮文案模板
        if action == "home_btntpl_set":
            key = parts[2] if len(parts) > 2 else "n_p"
            mapping = {
                "n_p": " {name} | ¥{price}",
                "p_n": " ¥{price} - {name}",
                "n_only": " {name}",
            }
            tpl = mapping.get(key, " {name} | ¥{price}")
            _set_setting("home.button_template", tpl)
            await _send_text(update.effective_chat.id, "已更新按钮文案模板", reply_markup=make_markup([row_back("adm:home")]))
            return

        # 商品排序（整页）：进入文本输入模式
        if action == "psort":
            # 格式：adm:psort:{page}
            page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            page_size = 10
            offset = (page - 1) * page_size
            _ensure_product_sort_column()
            rows = cur.execute(
                "SELECT id, COALESCE(sort, id) AS s FROM products ORDER BY s DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            ids_line = " ".join(str(r[0]) for r in rows)
            ctx.user_data["adm_wait"] = {"type": "psort", "data": {"page": page, "ids": [int(r[0]) for r in rows]}}
            kb = make_markup([row_back(f"adm:plist:{page}")])
            await _send_text(update.effective_chat.id, f"请输入该页的新顺序（仅数字，空格分隔），例如：{ids_line}。\n未写到的将按原顺序排在后面。", reply_markup=kb)
            return

        # 商品排序：上移一位
        if action == "pmoveu":
            # 格式：adm:pmoveu:{pid}:{page}
            if len(parts) < 3:
                return
            pid = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            _ensure_product_sort_column()
            try:
                row = cur.execute("SELECT id, COALESCE(sort, id) AS s FROM products WHERE id=?", (pid,)).fetchone()
                if row:
                    cur_id, cur_s = int(row[0]), int(row[1])
                    # 找到在“当前显示顺序(按 s DESC, id DESC)”下的前一个（更靠上）邻居
                    nb = cur.execute(
                        "SELECT id, COALESCE(sort, id) AS s FROM products "
                        "WHERE (COALESCE(sort, id) > ?) OR (COALESCE(sort, id) = ? AND id > ?) "
                        "ORDER BY COALESCE(sort, id) ASC, id ASC LIMIT 1",
                        (cur_s, cur_s, cur_id)
                    ).fetchone()
                    if nb:
                        nb_id, nb_s = int(nb[0]), int(nb[1])
                        # 采用“提升到邻居之上一格”的策略，避免相等值交换无效
                        new_s = nb_s + 1
                        cur.execute("UPDATE products SET sort=? WHERE id=?", (new_s, cur_id))
                        conn.commit()
                try:
                    await update.callback_query.answer("已上移", show_alert=False)
                except Exception:
                    pass
            except Exception:
                pass
            # 刷新当前页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:plist:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 商品排序：下移一位
        if action == "pmoved":
            # 格式：adm:pmoved:{pid}:{page}
            if len(parts) < 3:
                return
            pid = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            _ensure_product_sort_column()
            try:
                row = cur.execute("SELECT id, COALESCE(sort, id) AS s FROM products WHERE id=?", (pid,)).fetchone()
                if row:
                    cur_id, cur_s = int(row[0]), int(row[1])
                    # 找到在“当前显示顺序(按 s DESC, id DESC)”下的后一个（更靠下）邻居
                    nb = cur.execute(
                        "SELECT id, COALESCE(sort, id) AS s FROM products "
                        "WHERE (COALESCE(sort, id) < ?) OR (COALESCE(sort, id) = ? AND id < ?) "
                        "ORDER BY COALESCE(sort, id) DESC, id DESC LIMIT 1",
                        (cur_s, cur_s, cur_id)
                    ).fetchone()
                    if nb:
                        nb_id, nb_s = int(nb[0]), int(nb[1])
                        new_s = nb_s - 1
                        cur.execute("UPDATE products SET sort=? WHERE id=?", (new_s, cur_id))
                        conn.commit()
                try:
                    await update.callback_query.answer("已下移", show_alert=False)
                except Exception:
                    pass
            except Exception:
                pass
            # 刷新当前页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:plist:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 订单列表（分页 + 状态 + 时间范围筛选）
        if action == "olist":
            page = 1
            status_key = "all"
            if len(parts) > 2 and parts[2].isdigit():
                page = int(parts[2])
            if len(parts) > 3:
                status_key = parts[3]
            await _send_order_list(update.effective_chat.id, page, status_key, ctx)
            return

        # 设置订单筛选时间范围（开始）
        if action == "of_setrange":
            status_key = parts[2] if len(parts) > 2 else "all"
            page = parts[3] if len(parts) > 3 else "1"
            ctx.user_data["adm_wait"] = {"type": "of_start", "data": {"status_key": status_key, "page": page}}
            await _send_text(update.effective_chat.id, "请输入【开始日期】(YYYY-MM-DD)，留空表示不限制：", reply_markup=make_markup([row_back(f"adm:olist:{page}:{status_key}")]))
            return

        # 搜索（启动）
        if action == "of_search":
            status_key = parts[2] if len(parts) > 2 else "all"
            page = parts[3] if len(parts) > 3 else "1"
            ctx.user_data["adm_wait"] = {"type": "osearch_q", "data": {"status_key": status_key, "page": page}}
            await _send_text(update.effective_chat.id, "请输入搜索关键词：\n- 支持用户ID/商品ID（精确）\n- 支持商品名/商户单号（模糊）", reply_markup=make_markup([row_back(f"adm:olist:{page}:{status_key}")]))
            return

        # 单个商品菜单
        if action == "p":
            pid = parts[2]
            await _send_product_page(update.effective_chat.id, pid)
            return

        # 单个订单详情
        if action == "o":
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:olist:1:all")]))
                return
            oid = parts[2]
            status_key = parts[3] if len(parts) > 3 else "all"
            back_page = parts[4] if len(parts) > 4 else "1"
            row = cur.execute(
                "SELECT o.id, o.user_id, o.product_id, o.amount, o.payment_method, COALESCE(o.status,'pending'), o.create_time, o.out_trade_no, p.name "
                "FROM orders o LEFT JOIN products p ON p.id=o.product_id WHERE o.id=?",
                (oid,)
            ).fetchone()
            if not row:
                await _send_text(update.effective_chat.id, "未找到该订单", reply_markup=make_markup([row_back(f"adm:olist:{back_page}:{status_key}")]))
                return
            _oid, uid, pid, amount, pm, st, cts, out_trade_no, pname = row
            txt = (
                f"订单 #{_oid}\n"
                f"用户ID：{uid}\n"
                f"商品：{pname or pid}\n"
                f"金额：¥{amount}\n"
                f"支付方式：{pm}\n"
                f"状态：{STATUS_ZH.get((st or '').lower(), st)}\n"
                f"下单时间：{_fmt_ts(cts)}\n"
                f"商户单号：{out_trade_no}"
            )
            btn_rows = []
            # 待支付可追加“标记为已支付”
            if (st or "").lower() == "pending":
                btn_rows.append([InlineKeyboardButton("✅ 标记为已支付", callback_data=f"adm:opaidc:{_oid}:{status_key}:{back_page}")])
            btn_rows.append(row_back(f"adm:olist:{back_page}:{status_key}"))
            btn_rows.append(row_home_admin())
            kb = make_markup(btn_rows)
            await _send_text(update.effective_chat.id, txt, reply_markup=kb)
            return

        # 数据库优化：VACUUM
        if action == "vacuum":
            try:
                # VACUUM 需要在非事务状态下执行；这里直接使用连接执行
                cur.execute("VACUUM")
                conn.commit()
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已完成数据库优化 (VACUUM)")
                except Exception:
                    pass
            except Exception:
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ VACUUM 执行失败")
                except Exception:
                    pass
            # 返回主菜单
            await _admin_menu(update, ctx)
            return

        # 客服设置主页
        if action == "support":
            cur_val = (_get_setting("support.contact", "")).strip()
            show = cur_val if cur_val else "(未设置)"
            kb = make_markup([
                [InlineKeyboardButton("✏️ 修改客服联系方式", callback_data="adm:support_edit")],
                row_home_admin(),
            ])
            text = (
                "🆘 客服设置\n"
                f"当前值：{show}\n\n"
                "支持以下格式：\n"
                "- 直接填写链接：https://t.me/username\n"
                "- 用户名：@username\n"
                "- 纯文本：将作为说明文本展示给用户\n"
            )
            await _send_text(update.effective_chat.id, text, reply_markup=kb, disable_web_page_preview=True)
            return

        # 客服设置：进入编辑
        if action == "support_edit":
            ctx.user_data["adm_wait"] = {"type": "support_contact", "data": {}}
            kb = make_markup([row_back("adm:support")])
            await _send_text(update.effective_chat.id, "请输入新的【客服联系方式】：", reply_markup=kb)
            return

        # 公告设置：查看/编辑
        if action == "announcement":
            # 获取各支付方式的公告开关状态
            usdt_enabled = _get_setting("announcement.usdt.enabled", "true") == "true"
            usdt_token188_enabled = _get_setting("announcement.usdt_token188.enabled", "true") == "true"
            alipay_enabled = _get_setting("announcement.alipay.enabled", "true") == "true"
            wxpay_enabled = _get_setting("announcement.wxpay.enabled", "true") == "true"
            
            status_text = (
                f"📊 各支付方式公告状态：\n"
                f"• USDT(柠檬): {'✅ 已启用' if usdt_enabled else '❌ 已关闭'}\n"
                f"• USDT(TOKEN188): {'✅ 已启用' if usdt_token188_enabled else '❌ 已关闭'}\n"
                f"• 支付宝: {'✅ 已启用' if alipay_enabled else '❌ 已关闭'}\n"
                f"• 微信支付: {'✅ 已启用' if wxpay_enabled else '❌ 已关闭'}\n\n"
            )
            
            kb = make_markup([
                [InlineKeyboardButton("✏️ USDT公告", callback_data="adm:announcement_edit:usdt")],
                [InlineKeyboardButton("✏️ 支付宝/微信公告", callback_data="adm:announcement_edit:alipay_wxpay")],
                [InlineKeyboardButton("⚙️ 公告开关设置", callback_data="adm:announcement_switches")],
                row_home_admin(),
            ])
            text = (
                "📢 支付公告设置\n\n"
                f"{status_text}"
                "💡 提示：\n"
                "• USDT和支付宝/微信使用不同的公告内容\n"
                "• 用户选择支付方式时会显示对应公告\n"
                "• 点击【我知道了，继续支付】后显示付款链接\n"
                "• 后台会并行加载付款链接，减少等待时间"
            )
            await _send_text(update.effective_chat.id, text, reply_markup=kb)
            return

        # 公告设置：进入编辑
        if action == "announcement_edit":
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误")
                return
            
            announcement_type = parts[2]  # usdt 或 alipay_wxpay
            
            # 获取当前公告内容
            current_text = (_get_setting(f"announcement.{announcement_type}.text", "")).strip()
            
            if announcement_type == "usdt":
                title = "USDT支付公告"
                default_text = (
                    "📢 USDT支付重要提醒\n\n\n"
                    "⚠️ 请注意手续费问题\n\n"
                    "🏦 交易所转账（火币/欧易/币安）\n"
                    "   会扣 1U 手续费\n"
                    "   商品价格 10U → 请转 11U\n"
                    "   否则到账不足，无法自动拉群\n\n"
                    "💳 钱包转账（推荐 ✅）\n"
                    "   支持 Bitpie / TP / imToken 等钱包\n"
                    "   直接按商品金额转（例：10U 转 10U）\n"
                    "   钱包自动扣矿工费，到账准确，更省钱！\n\n"
                    "⚡️ 付款即发货，1-3分钟快速到账\n"
                    "   机器人自动拉你进会员群 ✅"
                )
            else:
                title = "支付宝/微信支付公告"
                default_text = (
                    "📢 欢迎光临官方商店\n\n\n"
                    "💳 微信 / 支付宝付款说明\n\n"
                    "✅ 按提示金额准确付款即可\n"
                    "✅ 支持微信扫码、支付宝扫码\n"
                    "✅ 付款后请勿关闭页面\n\n"
                    "⚡️ 付款即发货，1-3分钟快速到账\n"
                    "   机器人自动拉你进会员群 ✅"
                )
            
            ctx.user_data["adm_wait"] = {"type": "announcement_text", "data": {"announcement_type": announcement_type}}
            kb = make_markup([
                [InlineKeyboardButton("🔄 使用默认公告", callback_data=f"adm:announcement_use_default:{announcement_type}")],
                row_back("adm:announcement")
            ])
            
            preview_text = current_text if current_text else f"(当前使用默认公告)\n\n{default_text}"
            
            await _send_text(
                update.effective_chat.id, 
                f"请输入新的【{title}】内容：\n\n"
                f"当前公告：\n{preview_text}\n\n"
                "💡 提示：\n"
                "- 支持多行文本\n"
                "- 支持Emoji表情\n"
                "- 建议简洁明了",
                reply_markup=kb
            )
            return
        
        # 使用默认公告
        if action == "announcement_use_default":
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误")
                return
            
            announcement_type = parts[2]
            _set_setting(f"announcement.{announcement_type}.text", "")
            await _send_text(update.effective_chat.id, "✅ 已恢复默认公告")
            await asyncio.sleep(1)
            
            # 返回公告设置页
            await adm_router(
                type("obj", (), {
                    "callback_query": type("q", (), {"data": "adm:announcement"})(),
                    "effective_user": update.effective_user,
                    "effective_chat": update.effective_chat,
                    "get_bot": update.get_bot
                })(),
                ctx
            )
            return

        # 公告设置：恢复默认
        if action == "announcement_reset":
            try:
                _set_setting("announcement.text", "")
                await _send_text(update.effective_chat.id, "✅ 已恢复默认公告")
                await asyncio.sleep(1)
            except Exception:
                pass
            # 返回公告设置页
            await adm_router(
                type("obj", (), {
                    "callback_query": type("q", (), {"data": "adm:announcement"})(),
                    "effective_user": update.effective_user,
                    "effective_chat": update.effective_chat,
                    "get_bot": update.get_bot
                })(),
                ctx
            )
            return

        # 公告开关设置页面
        if action == "announcement_switches":
            usdt_enabled = _get_setting("announcement.usdt.enabled", "true") == "true"
            usdt_token188_enabled = _get_setting("announcement.usdt_token188.enabled", "true") == "true"
            alipay_enabled = _get_setting("announcement.alipay.enabled", "true") == "true"
            wxpay_enabled = _get_setting("announcement.wxpay.enabled", "true") == "true"
            
            kb = make_markup([
                [InlineKeyboardButton(
                    f"{'✅' if usdt_enabled else '❌'} USDT(柠檬)", 
                    callback_data="adm:announcement_toggle:usdt"
                )],
                [InlineKeyboardButton(
                    f"{'✅' if usdt_token188_enabled else '❌'} USDT(TOKEN188)", 
                    callback_data="adm:announcement_toggle:usdt_token188"
                )],
                [InlineKeyboardButton(
                    f"{'✅' if alipay_enabled else '❌'} 支付宝", 
                    callback_data="adm:announcement_toggle:alipay"
                )],
                [InlineKeyboardButton(
                    f"{'✅' if wxpay_enabled else '❌'} 微信支付", 
                    callback_data="adm:announcement_toggle:wxpay"
                )],
                row_back("adm:announcement"),
            ])
            
            text = (
                "⚙️ 公告开关设置\n\n"
                "点击按钮切换各支付方式的公告开关：\n\n"
                f"• USDT(柠檬): {'✅ 已启用' if usdt_enabled else '❌ 已关闭'}\n"
                f"• USDT(TOKEN188): {'✅ 已启用' if usdt_token188_enabled else '❌ 已关闭'}\n"
                f"• 支付宝: {'✅ 已启用' if alipay_enabled else '❌ 已关闭'}\n"
                f"• 微信支付: {'✅ 已启用' if wxpay_enabled else '❌ 已关闭'}\n\n"
                "💡 启用后，用户选择该支付方式时会先显示公告"
            )
            await _send_text(update.effective_chat.id, text, reply_markup=kb)
            return

        # 切换公告开关
        if action == "announcement_toggle":
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误")
                return
            
            channel = parts[2]
            current_status = _get_setting(f"announcement.{channel}.enabled", "true")
            new_status = "false" if current_status == "true" else "true"
            _set_setting(f"announcement.{channel}.enabled", new_status)
            
            # 返回开关设置页
            await adm_router(
                type("obj", (), {
                    "callback_query": type("q", (), {"data": "adm:announcement_switches"})(),
                    "effective_user": update.effective_user,
                    "effective_chat": update.effective_chat,
                    "get_bot": update.get_bot
                })(),
                ctx
            )
            return

        # 订单删除：弹出确认
        if action == "odelc":
            # 格式：adm:odelc:{oid}:{status_key}:{page}
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:olist:1:all")]))
                return
            oid = parts[2]
            status_key = parts[3] if len(parts) > 3 else "all"
            page = parts[4] if len(parts) > 4 else "1"
            kb = make_markup([
                [
                    InlineKeyboardButton("✅ 确认删除", callback_data=f"adm:odel:{oid}:{status_key}:{page}"),
                    InlineKeyboardButton("❌ 取消", callback_data=f"adm:odelx:{status_key}:{page}")
                ]
            ])
            await _send_text(update.effective_chat.id, f"确认删除订单 #{oid}？此操作不可恢复。", reply_markup=kb)
            return

        # 订单删除：执行硬删除
        if action == "odel":
            # 格式：adm:odel:{oid}:{status_key}:{page}
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:olist:1:all")]))
                return
            oid = parts[2]
            status_key = parts[3] if len(parts) > 3 else "all"
            page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
            try:
                cur.execute("DELETE FROM orders WHERE id=?", (oid,))
                conn.commit()
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已删除订单，返回列表…", ttl=2)
            except Exception:
                # 删除失败也返回列表
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 删除失败，已返回列表。", ttl=3)
                except Exception:
                    pass
            await _send_order_list(update.effective_chat.id, page, status_key, ctx)
            return

        # 订单删除：取消并返回当前列表
        if action == "odelx":
            # 格式：adm:odelx:{status_key}:{page}
            status_key = parts[2] if len(parts) > 2 else "all"
            page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            await _send_order_list(update.effective_chat.id, page, status_key, ctx)
            return

        # 订单人工回调：确认弹窗
        if action == "opaidc":
            # 格式：adm:opaidc:{oid}:{status_key}:{page}
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:olist:1:all")]))
                return
            oid = parts[2]
            status_key = parts[3] if len(parts) > 3 else "all"
            page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
            kb = make_markup([
                [
                    InlineKeyboardButton("✅ 确认标记为已支付", callback_data=f"adm:opaid:{oid}:{status_key}:{page}"),
                    InlineKeyboardButton("❌ 取消", callback_data=f"adm:o:{oid}:{status_key}:{page}")
                ]
            ])
            await _send_text(update.effective_chat.id, f"确认将订单 #{oid} 标记为已支付并发放邀请链接？", reply_markup=kb)
            return

        # 订单人工回调：标记为已支付并发邀请
        if action == "opaid":
            # 格式：adm:opaid:{oid}:{status_key}:{page}
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:olist:1:all")]))
                return
            oid = parts[2]
            status_key = parts[3] if len(parts) > 3 else "all"
            page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
            try:
                row = cur.execute("SELECT out_trade_no, COALESCE(status,'pending') FROM orders WHERE id=?", (oid,)).fetchone()
                if not row:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 未找到该订单", ttl=2)
                    # 返回详情页（如果找不到也回列表）
                    await _send_order_list(update.effective_chat.id, page, status_key, ctx)
                    return
                out_trade_no, st = row
                if (st or "").lower() not in ("pending", "paid"):
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "⚠️ 订单状态不可标记为已支付", ttl=2)
                    # 返回详情
                    await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:o:{oid}:{status_key}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
                    return
                if not out_trade_no:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 订单缺少商户单号", ttl=2)
                    await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:o:{oid}:{status_key}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
                    return
                if callable(mark_paid_and_send_invite):
                    try:
                        mark_paid_and_send_invite(out_trade_no)
                        await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已标记为已支付，正在发放自动拉群邀请…", ttl=3)
                    except Exception:
                        await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 标记失败，请稍后重试", ttl=3)
                else:
                    # 兜底：仅置为 paid
                    try:
                        cur.execute("UPDATE orders SET status='paid' WHERE id=?", (oid,))
                        conn.commit()
                        await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已标记为已支付", ttl=2)
                    except Exception:
                        await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 数据库更新失败", ttl=2)
            except Exception:
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 处理失败", ttl=2)
                except Exception:
                    pass
            # 返回订单详情页以展示最新状态
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:o:{oid}:{status_key}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 统计报表（支持时间范围 + TopN + ASCII图）
        if action == "ostat":
            # 默认落在“今日”
            if not ctx.user_data.get("adm_sfilter"):
                now = time.localtime()
                day_start = int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
                ctx.user_data["adm_sfilter"] = {"start_ts": day_start, "end_ts": int(time.time())}
            await _send_stat_page(update.effective_chat.id, ctx)
            try:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 刷新完成", ttl=2)
            except Exception:
                pass
            return

        # 统计范围快捷切换：今日/本月/本年（对齐自然区间）
        if action in {"sf_today", "sf_month", "sf_year"}:
            now = time.localtime()
            # 当天 00:00
            day_start = int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
            if action == "sf_today":
                start_ts = day_start
            elif action == "sf_month":
                # 本月1号 00:00
                start_ts = int(time.mktime((now.tm_year, now.tm_mon, 1, 0, 0, 0, 0, 0, now.tm_isdst)))
            else:  # sf_year
                # 当年1月1日 00:00
                start_ts = int(time.mktime((now.tm_year, 1, 1, 0, 0, 0, 0, 0, now.tm_isdst)))
            end_ts = int(time.time())
            ctx.user_data["adm_sfilter"] = {"start_ts": start_ts, "end_ts": end_ts}
            label = {"sf_today": "今日", "sf_month": "本月", "sf_year": "本年"}[action]
            await send_ephemeral(update.get_bot(), update.effective_chat.id, f"✅ 已切换统计范围：{label}，正在刷新…", ttl=2)
            await _send_stat_page(update.effective_chat.id, ctx)
            return

        # 新增商品 - 启动流程
        if action == "pnew":
            ctx.user_data["adm_wait"] = {"type": "pnew_name", "data": {}}
            kb = make_markup([row_home_admin()])
            await _send_text(update.effective_chat.id, "请输入新商品【名称】：", reply_markup=kb)
            return

        # 删除商品
        if action == "del":
            pid = parts[2]
            cur.execute("DELETE FROM products WHERE id=?", (pid,))
            conn.commit()
            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已删除，返回列表…", ttl=2)
            # 返回列表
            await _send_text(
                update.effective_chat.id,
                "📦 商品列表",
                reply_markup=make_markup([
                    [InlineKeyboardButton("刷新列表", callback_data="adm:plist:1")],
                    row_home_admin(),
                ]),
            )
            return

        # 上/下架
        if action == "toggle":
            pid = parts[2]
            row = cur.execute("SELECT COALESCE(status,'on') FROM products WHERE id=?", (pid,)).fetchone()
            if not row:
                kb = make_markup([
                    [InlineKeyboardButton("📋 返回列表", callback_data="adm:plist:1")],
                    row_home_admin(),
                ])
                await _send_text(update.effective_chat.id, "⚠️ 未找到该商品", reply_markup=kb)
                return
            cur_status = row[0] or 'on'
            new_status = 'off' if cur_status == 'on' else 'on'
            cur.execute("UPDATE products SET status=? WHERE id=?", (new_status, pid))
            conn.commit()
            await send_ephemeral(update.get_bot(), update.effective_chat.id, f"✅ 已{'下架' if new_status=='off' else '上架'}，返回商品页…", ttl=2)
            # 返回单品页面（直接渲染，避免伪回调）
            try:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "正在刷新…", ttl=2)
            except Exception:
                pass
            await _send_product_page(update.effective_chat.id, pid)
            try:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 刷新完成", ttl=2)
            except Exception:
                pass
            return

        # 主页编辑菜单
        if action == "home":
            await _send_home_menu(update.effective_chat.id)
            return

        # 主页预览
        if action == "home_preview":
            await _send_home_preview(update.effective_chat.id)
            return

        # 主页编辑 - 启动等待态
        if action in {"home_title", "home_intro", "home_cover"}:
            kind = action.split("_")[1]  # title/intro/cover
            ctx.user_data["adm_wait"] = {"type": f"home_{kind}", "data": {}}
            prompt = {
                "title": "请输入新的【主页标题】：",
                "intro": "请输入新的【主页简介】：",
                "cover": "请发送新的【封面】：可直接发图片（将保存 file_id），或发图片URL",
            }[kind]
            kb = make_markup([row_back("adm:home")])
            await _send_text(update.effective_chat.id, prompt, reply_markup=kb)
            return

        # 编辑商品发货方式：改为内联按钮选择
        if action == "edit_deliver":
            # 格式：adm:edit_deliver:{pid}
            pid = parts[2]
            kb = make_markup([
                [
                    InlineKeyboardButton("👥 自动拉群", callback_data=f"adm:set_deliver:{pid}:join_group"),
                    InlineKeyboardButton("🧷 通用卡密", callback_data=f"adm:set_deliver:{pid}:card_fixed"),
                    InlineKeyboardButton("🔑 卡池", callback_data=f"adm:set_deliver:{pid}:card_pool"),
                ],
                row_back(f"adm:p:{pid}")
            ])
            await _send_text(update.effective_chat.id, "请选择【发货方式】：", reply_markup=kb)
            return

        # 发货方式保存
        if action == "set_deliver":
            # 格式：adm:set_deliver:{pid}:{method}
            if len(parts) < 4:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_back("adm:plist:1")]))
                return
            pid = parts[2]
            method = parts[3]
            if method not in {"join_group", "card_fixed", "card_pool"}:
                kb = make_markup([row_back(f"adm:p:{pid}")])
                await _send_text(update.effective_chat.id, "不支持的发货方式", reply_markup=kb)
                return
            try:
                cur.execute("UPDATE products SET deliver_type=? WHERE id=?", (method, pid))
                conn.commit()
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已保存发货方式，返回商品页…", ttl=2)
            except Exception:
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 保存失败", ttl=2)
                except Exception:
                    pass
            # 返回商品页
            await _send_product_page(update.effective_chat.id, pid)
            return

        # 新增商品：选择发货方式（内联按钮回调）
        if action == "pnew_set_deliver":
            # 格式：adm:pnew_set_deliver:{method}
            if len(parts) < 3:
                await _send_text(update.effective_chat.id, "参数错误", reply_markup=make_markup([row_home_admin()]))
                return
            method = parts[2]
            # 仅在新增商品等待选择阶段有效
            state = ctx.user_data.get("adm_wait") or {}
            if state.get("type") != "pnew_wait_deliver":
                await _send_text(update.effective_chat.id, "未处于新增商品的发货方式选择阶段，请重新开始新增商品流程。", reply_markup=make_markup([row_back("adm:plist:1")]))
                return
            data = state.get("data") or {}
            name = data.get("name")
            price = data.get("price")
            desc = data.get("desc")
            cover = data.get("cover")
            if method not in {"join_group", "card_fixed", "card_pool"}:
                await _send_text(update.effective_chat.id, "不支持的发货方式", reply_markup=make_markup([row_back("adm:plist:1")]))
                return
            if method == "join_group":
                # 先选择了自动拉群，再去填写群ID
                state["data"]["deliver_type"] = method
                ctx.user_data["adm_wait"] = {"type": "pnew_group", "data": state["data"]}
                kb = make_markup([row_home_admin()])
                await _send_text(update.effective_chat.id, "请输入目标群组ID（需为机器人所在群，且机器人为管理员）：", reply_markup=kb)
                return
            # 其它发货方式：立即创建，群ID置为空字符串
            try:
                cur.execute(
                    "INSERT INTO products(name, price, full_description, cover_url, tg_group_id, deliver_type) VALUES (?,?,?,?,?,?)",
                    (name, price, desc, cover, "", method),
                )
                conn.commit()
                pid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
            except Exception:
                await _send_text(update.effective_chat.id, "保存失败，请稍后重试。", reply_markup=make_markup([row_back("adm:plist:1")]))
                return
            ctx.user_data.pop("adm_wait", None)
            await _send_text(update.effective_chat.id, "✅ 新商品已创建，返回商品页…", reply_markup=make_markup([row_back(f"adm:p:{pid}")]))
            await _send_product_page(update.effective_chat.id, str(pid))
            return

        # 编辑商品字段 - 启动等待态
        if action.startswith("edit_"):
            field = action.split(":")[0][5:]  # name/price/desc/cover/group/deliver/card_fixed
            pid = parts[2]
            ctx.user_data["adm_wait"] = {"type": f"edit_{field}", "data": {"pid": pid}}
            asks = {
                "name": "请输入新的【商品名称】：",
                "price": "请输入新的【价格】（数字）：",
                "desc": "请输入新的【详情描述】：",
                "cover": "请发送新的【封面】：可直接发图片（保存 file_id）或发URL",
                "group": "请输入新的【群组ID】：例如 -1001234567890",
                "deliver": "发货方式已改为按钮选择，请点击上方“发货方式”按钮进行设置。若未看到按钮，请返回商品页重试。",
                "card_fixed": "请输入新的【通用卡密】：",
            }
            kb = make_markup([row_back(f"adm:p:{pid}")])
            await _send_text(update.effective_chat.id, asks[field], reply_markup=kb)
            return

        # 卡池管理页面
        if action == "card_pool":
            # 格式：adm:card_pool:{pid}:{page}
            if len(parts) < 3:
                return
            pid = parts[2]
            try:
                page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            except Exception:
                page = 1
            page = max(1, page)
            page_size = 10
            try:
                stock_row = cur.execute("SELECT COUNT(*) FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL", (pid,)).fetchone()
                stock_cnt = int(stock_row[0] or 0)
            except Exception:
                stock_cnt = 0
            try:
                used_row = cur.execute("SELECT COUNT(*) FROM card_keys WHERE product_id=? AND used_by_order_id IS NOT NULL", (pid,)).fetchone()
                used_cnt = int(used_row[0] or 0)
            except Exception:
                used_cnt = 0
            total_pages = (stock_cnt + page_size - 1) // page_size if stock_cnt > 0 else 1
            if page > total_pages:
                page = total_pages
            offset = (page - 1) * page_size
            # 分页预览未使用卡密
            rows = []
            try:
                rows = cur.execute(
                    "SELECT id, key_text FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL ORDER BY id ASC LIMIT ? OFFSET ?",
                    (pid, page_size, offset)
                ).fetchall()
            except Exception:
                rows = []
            preview = "\n".join([f"#{r[0]} {str(r[1])[:60]}" for r in rows]) if rows else "(本页暂无未使用卡密)"
            text = (
                f"🔑 商品 #{pid} 的卡密库存\n"
                f"未使用：{stock_cnt}  |  已使用：{used_cnt}\n"
                f"页码：{page}/{max(1,total_pages)}\n\n"
                f"预览（每页最多{page_size}条，未使用）：\n{preview}"
            )
            # 删除按钮（每行放置最多 5 个）
            del_btns = []
            row_buf = []
            for _id, _ in rows:
                row_buf.append(InlineKeyboardButton(f"❌#{_id}", callback_data=f"adm:cp_del:{pid}:{_id}:{page}"))
                if len(row_buf) >= 5:
                    del_btns.append(row_buf)
                    row_buf = []
            if row_buf:
                del_btns.append(row_buf)
            # 翻页按钮
            nav = []
            if page > 1:
                nav.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"adm:card_pool:{pid}:{page-1}"))
            if page < total_pages:
                nav.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"adm:card_pool:{pid}:{page+1}"))
            kb_rows = [
                [InlineKeyboardButton("📥 导入卡密", callback_data=f"adm:cp_import:{pid}"), InlineKeyboardButton("⬇️ 导出未用", callback_data=f"adm:cp_export:{pid}"), InlineKeyboardButton("🧹 清空未用", callback_data=f"adm:cp_clearc:{pid}")],
                [InlineKeyboardButton("🧽 去重未用", callback_data=f"adm:cp_dedupc:{pid}:{page}"), InlineKeyboardButton("🗑 删除已用", callback_data=f"adm:cp_clear_usedc:{pid}")],
            ]
            if del_btns:
                kb_rows.extend(del_btns)
            if nav:
                kb_rows.append(nav)
            kb_rows.append(row_back(f"adm:p:{pid}"))
            kb_rows.append(row_home_admin())
            kb = make_markup(kb_rows)
            await _send_text(update.effective_chat.id, text, reply_markup=kb)
            return

        # 卡池导入：进入等待态
        if action == "cp_import":
            pid = parts[2]
            ctx.user_data["adm_wait"] = {"type": "cp_import", "data": {"pid": pid}}
            kb = make_markup([row_back(f"adm:card_pool:{pid}:1")])
            await _send_text(update.effective_chat.id, "请粘贴要导入的卡密文本：\n- 每行一条\n- 将自动忽略空行\n- 同一商品下的重复行会被跳过", reply_markup=kb)
            return

        # 卡池清空未用：确认
        if action == "cp_clearc":
            pid = parts[2]
            kb = make_markup([
                [InlineKeyboardButton("✅ 确认清空未使用", callback_data=f"adm:cp_clear:{pid}"), InlineKeyboardButton("❌ 取消", callback_data=f"adm:card_pool:{pid}:1")]
            ])
            await _send_text(update.effective_chat.id, f"确认清空商品 #{pid} 的未使用卡密吗？此操作不可恢复。", reply_markup=kb)
            return

        # 卡池清空未用：执行
        if action == "cp_clear":
            pid = parts[2]
            try:
                cur.execute("DELETE FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL", (pid,))
                conn.commit()
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已清空未使用卡密", ttl=2)
            except Exception:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 清空失败", ttl=2)
            # 返回卡池页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:1"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 卡池删除已使用：确认
        if action == "cp_clear_usedc":
            pid = parts[2]
            kb = make_markup([
                [InlineKeyboardButton("✅ 确认删除已使用", callback_data=f"adm:cp_clear_used:{pid}"), InlineKeyboardButton("❌ 取消", callback_data=f"adm:card_pool:{pid}:1")]
            ])
            await _send_text(update.effective_chat.id, f"确认删除商品 #{pid} 的已使用卡密吗？此操作不可恢复。", reply_markup=kb)
            return

        # 卡池删除已使用：执行
        if action == "cp_clear_used":
            pid = parts[2]
            try:
                cur.execute("DELETE FROM card_keys WHERE product_id=? AND used_by_order_id IS NOT NULL", (pid,))
                conn.commit()
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已删除已使用卡密", ttl=2)
            except Exception:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 删除失败", ttl=2)
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:1"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 单条删除未使用卡密
        if action == "cp_del":
            # 格式：adm:cp_del:{pid}:{key_id}:{page}
            if len(parts) < 4:
                return
            pid = parts[2]
            try:
                key_id = int(parts[3])
            except Exception:
                key_id = None
            try:
                page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
            except Exception:
                page = 1
            if key_id is None:
                await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
                return
            try:
                # 仅删除未使用的目标 id
                cur.execute("DELETE FROM card_keys WHERE id=? AND product_id=? AND used_by_order_id IS NULL", (key_id, pid))
                conn.commit()
                await send_ephemeral(update.get_bot(), update.effective_chat.id, f"✅ 已删除 #{key_id}", ttl=2)
            except Exception:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, f"❗ 删除失败 #{key_id}", ttl=2)
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 去重未用：确认
        if action == "cp_dedupc":
            pid = parts[2]
            try:
                page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            except Exception:
                page = 1
            kb = make_markup([
                [InlineKeyboardButton("✅ 确认去重未用", callback_data=f"adm:cp_dedup:{pid}:{page}"), InlineKeyboardButton("❌ 取消", callback_data=f"adm:card_pool:{pid}:{page}")]
            ])
            await _send_text(update.effective_chat.id, f"将删除相同内容的重复未使用卡密，仅保留每组的最早一条。确定继续？", reply_markup=kb)
            return

        # 去重未用：执行
        if action == "cp_dedup":
            pid = parts[2]
            try:
                page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
            except Exception:
                page = 1
            # 扫描未使用卡密并删除重复（同 key_text, 仅保留最小 id）
            try:
                rows = cur.execute("SELECT id, key_text FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL ORDER BY id ASC", (pid,)).fetchall()
            except Exception:
                rows = []
            seen = set()
            to_del = []
            for rid, k in rows:
                k = str(k)
                if k in seen:
                    to_del.append(int(rid))
                else:
                    seen.add(k)
            removed = 0
            if to_del:
                # 分批删除，避免 SQL 变量过多
                chunk = 200
                for i in range(0, len(to_del), chunk):
                    ids = to_del[i:i+chunk]
                    qmarks = ",".join(["?"] * len(ids))
                    try:
                        cur.execute(f"DELETE FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL AND id IN ({qmarks})", (pid, *ids))
                        conn.commit()
                        removed += len(ids)
                    except Exception:
                        pass
            await send_ephemeral(update.get_bot(), update.effective_chat.id, f"✅ 去重完成，删除 {removed} 条", ttl=3)
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        if action == "menu":
            await _admin_menu(update, ctx)
            return

        # 导出未使用卡密为文本
        if action == "cp_export":
            pid = parts[2]
            try:
                rows = cur.execute(
                    "SELECT key_text FROM card_keys WHERE product_id=? AND used_by_order_id IS NULL ORDER BY id ASC",
                    (pid,)
                ).fetchall()
            except Exception:
                rows = []
            if not rows:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "暂无未使用卡密可导出", ttl=2)
                await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:1"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
                return
            content = "\n".join([str(r[0]) for r in rows])
            try:
                bio = io.BytesIO(content.encode("utf-8"))
                filename = f"product_{pid}_unused_{int(time.time())}.txt"
                bio.name = filename
                await app.bot.send_document(chat_id=update.effective_chat.id, document=bio, caption=f"商品 #{pid} 未使用卡密导出，共 {len(rows)} 条")
            except Exception:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "导出失败", ttl=2)
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:1"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

    async def adm_text_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _guard_admin(update):
            return
        state = ctx.user_data.get("adm_wait")
        if not state:
            return
        kind = state.get("type")
        # 兼容图片消息
        msg = update.message
        text = (getattr(msg, "text", None) or "").strip()

        async def _check_and_warn_bot_admin(gid_text: str) -> bool:
            try:
                # 将群ID尽量转为 int，Telegram 超级群通常形如 -100xxxxxxxxxx
                try:
                    gid_int = int(gid_text)
                except Exception:
                    gid_int = gid_text
                me = await app.bot.get_me()
                bot_id = getattr(me, "id", None)
                if not bot_id:
                    return False
                cm = await app.bot.get_chat_member(chat_id=gid_int, user_id=bot_id)
                status = getattr(cm, "status", "")
                if status not in ("administrator", "creator"):
                    try:
                        await update.message.reply_text("⚠️ 注意：机器人不是该群的管理员，自动拉群邀请与撤销可能失败。请将机器人设为管理员后再使用。")
                    except Exception:
                        pass
                    return False
                return True
            except Exception:
                # 验证失败不阻断流程，仅忽略
                return False

        # 设置订单筛选开始日期（订单列表）
        if kind == "of_start":
            status_key = state["data"].get("status_key", "all")
            page = state["data"].get("page", "1")
            s = text
            start_ts = _parse_date(s)
            # 不限制留空
            if s == "":
                start_ts = None
            ctx.user_data.setdefault("adm_ofilter", {})["start_ts"] = start_ts
            ctx.user_data["adm_wait"] = {"type": "of_end", "data": {"status_key": status_key, "page": page}}
            kb = make_markup([row_back(f"adm:olist:{page}:{status_key}")])
            await update.message.reply_text("请输入【结束日期】(YYYY-MM-DD)，留空表示不限制：", reply_markup=kb)
            return

        if kind == "of_end":
            status_key = state["data"].get("status_key", "all")
            page = int(state["data"].get("page", "1"))
            s = text
            end_ts = _parse_date(s)
            if s == "":
                end_ts = None
            # 包含当日 23:59:59
            if end_ts is not None:
                end_ts = end_ts + 86399
            ctx.user_data.setdefault("adm_ofilter", {})["end_ts"] = end_ts
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已设置时间范围，返回订单列表…", ttl=2)
            await _send_order_list(update.effective_chat.id, page, status_key, ctx)
            return

        # 搜索关键词输入
        if kind == "osearch_q":
            status_key = state["data"].get("status_key", "all")
            page = int(state["data"].get("page", "1"))
            qkw = text.strip()
            if qkw == "":
                # 为空等价清除
                ctx.user_data.pop("adm_osearch", None)
                tip = "✅ 已清除搜索条件，返回订单列表…"
            else:
                ctx.user_data["adm_osearch"] = {"q": qkw}
                tip = "✅ 已设置搜索条件，返回订单列表…"
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, tip, ttl=2)
            await _send_order_list(update.effective_chat.id, page, status_key, ctx)
            return

        # 保存客服联系方式（客服设置）
        if kind == "support_contact":
            val = text
            try:
                _set_setting("support.contact", val)
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已保存客服联系方式", ttl=2)
            except Exception:
                try:
                    await send_ephemeral(update.get_bot(), update.effective_chat.id, "❗ 保存失败", ttl=2)
                except Exception:
                    pass
            ctx.user_data.pop("adm_wait", None)
            # 返回客服设置主页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": "adm:support"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 保存公告内容（公告设置）
        if kind == "announcement_text":
            val = text.strip()
            announcement_type = state.get("data", {}).get("announcement_type", "usdt")  # 默认为usdt
            try:
                _set_setting(f"announcement.{announcement_type}.text", val)
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已保存公告内容", ttl=2)
            except Exception:
                try:
                    await _send_text(update.effective_chat.id, "❌ 保存失败")
                except Exception:
                    pass
            ctx.user_data.pop("adm_wait", None)
            # 返回公告设置主页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": "adm:announcement"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 卡池导入：处理文本
        if kind == "cp_import":
            pid = state["data"].get("pid")
            # 拆分行，去空白
            lines = [ln.strip() for ln in (text or "").splitlines()]
            lines = [ln for ln in lines if ln]
            if not lines:
                kb = make_markup([row_back(f"adm:card_pool:{pid}:1")])
                await update.message.reply_text("未检测到有效内容，请重新粘贴。", reply_markup=kb)
                return
            # 去重（同一商品范围内）
            try:
                exist_rows = cur.execute("SELECT key_text FROM card_keys WHERE product_id=?", (pid,)).fetchall()
                exist_set = set(str(r[0]) for r in exist_rows)
            except Exception:
                exist_set = set()
            to_insert = [(pid, ln, int(time.time())) for ln in lines if ln not in exist_set]
            inserted = 0
            if to_insert:
                try:
                    cur.executemany("INSERT INTO card_keys(product_id, key_text, create_time) VALUES (?,?,?)", to_insert)
                    conn.commit()
                    inserted = len(to_insert)
                except Exception:
                    inserted = 0
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, f"✅ 导入完成，本次新增 {inserted} 条", ttl=3)
            # 返回卡池页面
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:card_pool:{pid}:1"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 统计页设置开始日期
        if kind == "sf_start":
            s = text
            start_ts = _parse_date(s)
            if s == "":
                start_ts = None
            ctx.user_data.setdefault("adm_sfilter", {})["start_ts"] = start_ts
            ctx.user_data["adm_wait"] = {"type": "sf_end", "data": {}}
            kb = make_markup([row_back("adm:ostat")])
            await update.message.reply_text("请输入【结束日期】(YYYY-MM-DD)，留空表示不限制：", reply_markup=kb)
            return

        if kind == "sf_end":
            s = text
            end_ts = _parse_date(s)
            if s == "":
                end_ts = None
            if end_ts is not None:
                end_ts = end_ts + 86399
            ctx.user_data.setdefault("adm_sfilter", {})["end_ts"] = end_ts
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已设置统计时间范围，返回统计…", ttl=2)
            await _send_stat_page(update.effective_chat.id, ctx)
            return

        # 商品排序（整页）：按输入的 ID 序列重排当前页
        if kind == "psort":
            try:
                page = int(state.get("data", {}).get("page", 1))
            except Exception:
                page = 1
            ids_in_page = state.get("data", {}).get("ids", [])
            # 解析输入：支持 "#1 #2 3 4" 形式
            import re as _re
            toks = [t for t in _re.split(r"[\s,，;；]+", text) if t]
            parsed_ids = []
            for t in toks:
                t = t.strip()
                if t.startswith("#"):
                    t = t[1:]
                if t.isdigit():
                    try:
                        parsed_ids.append(int(t))
                    except Exception:
                        pass
            # 去重并仅保留本页存在的 ID
            seen = set()
            parsed_ids_unique = []
            for _id in parsed_ids:
                if _id in seen:
                    continue
                seen.add(_id)
                if _id in ids_in_page:
                    parsed_ids_unique.append(_id)
            # 目标顺序 = 用户指定的在前 + 其余未指定的按原顺序在后
            rest_ids = [i for i in ids_in_page if i not in set(parsed_ids_unique)]
            new_order_ids = parsed_ids_unique + rest_ids

            # 读取当前页的 sort 值集合（按当前显示顺序：s DESC, id DESC）
            page_size = 10
            offset = (page - 1) * page_size
            _ensure_product_sort_column()
            rows = cur.execute(
                "SELECT id, COALESCE(sort, id) AS s FROM products ORDER BY s DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            # 构造 id -> s 映射，并取按当前顺序排列的 s 值列表
            id_to_s = {int(r[0]): int(r[1]) for r in rows}
            s_vals_current_order = [int(r[1]) for r in rows]
            # 仅重排本页这些 ID：用同一组 s 值重新分配，保持与其它页的相对位置
            updates = []
            for idx, pid in enumerate(new_order_ids):
                if pid in id_to_s and idx < len(s_vals_current_order):
                    new_s = s_vals_current_order[idx]
                    if id_to_s.get(pid) != new_s:
                        updates.append((new_s, pid))
            if updates:
                try:
                    cur.executemany("UPDATE products SET sort=? WHERE id=?", updates)
                    conn.commit()
                except Exception:
                    pass
            # 结束等待并反馈
            ctx.user_data.pop("adm_wait", None)
            try:
                await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已更新排序", ttl=2)
            except Exception:
                pass
            # 刷新当前页
            await adm_router(type("obj", (), {"callback_query": type("q", (), {"data": f"adm:plist:{page}"}), "effective_user": update.effective_user, "effective_chat": update.effective_chat, "get_bot": update.get_bot})(), ctx)
            return

        # 新增商品流程：name -> price -> desc -> cover -> group -> save
        if kind == "pnew_name":
            state["type"] = "pnew_price"
            state["data"]["name"] = text
            kb = make_markup([row_home_admin()])
            await update.message.reply_text("请输入【价格】（数字）：", reply_markup=kb)
            return
        if kind == "pnew_price":
            try:
                price = float(text)
            except Exception:
                kb = make_markup([row_home_admin()])
                await update.message.reply_text("格式不正确，请输入数字价格：", reply_markup=kb)
                return
            state["type"] = "pnew_desc"
            state["data"]["price"] = price
            kb = make_markup([row_home_admin()])
            await update.message.reply_text("请输入【详情描述】：（可换行，尽量简洁）", reply_markup=kb)
            return
        if kind == "pnew_desc":
            state["type"] = "pnew_cover"
            state["data"]["desc"] = text
            kb = make_markup([row_home_admin()])
            await update.message.reply_text("请发送【封面】：可直接发送图片（将保存为 file_id），或发送图片 URL。请务必提供。", reply_markup=kb)
            return
        if kind == "pnew_cover":
            name = state["data"].get("name")
            price = state["data"].get("price")
            desc = state["data"].get("desc")
            # 支持直接发送图片作为封面
            cover = None
            try:
                photos = getattr(msg, "photo", None)
                if photos:
                    cover = photos[-1].file_id
                    try:
                        await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已收到图片封面，正在保存…", ttl=2)
                    except Exception:
                        pass
                elif text:
                    cover = text
            except Exception:
                cover = text if text else None
            state["data"]["cover"] = cover
            # 直接创建商品：默认发货方式设为 join_group（自动拉群，可在商品页修改）
            try:
                cur.execute(
                    "INSERT INTO products(name, price, full_description, cover_url, tg_group_id, deliver_type) VALUES (?,?,?,?,?,?)",
                    (name, price, desc, cover, "", "join_group"),
                )
                conn.commit()
                pid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
            except Exception:
                kb = make_markup([row_home_admin()])
                await update.message.reply_text("保存失败，请稍后重试。", reply_markup=kb)
                return
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 新商品已创建（发货方式默认为自动拉群，可在商品页修改）…", ttl=2)
            await _send_product_page(update.effective_chat.id, str(pid))
            return

        if kind == "pnew_group":
            gid = text
            if not gid:
                kb = make_markup([row_home_admin()])
                await update.message.reply_text("群组ID 不能为空，请重新输入：", reply_markup=kb)
                return
            # 简单校验：必须以 -100 开头或为纯数字
            ok = gid.startswith("-100") or gid.lstrip("-").isdigit()
            if not ok:
                kb = make_markup([row_home_admin()])
                await update.message.reply_text("格式不正确，请输入正确的群组ID，例如 -1001234567890：", reply_markup=kb)
                return
            # 强校验：机器人必须是该群管理员，否则不允许保存，停留在本步骤重试
            ok_admin = await _check_and_warn_bot_admin(gid)
            if not ok:
                kb = make_markup([row_home_admin()])
                await update.message.reply_text("已取消保存。请为机器人授予群管理员后，重新输入群组ID：", reply_markup=kb)
                # 继续等待同一步骤输入
                ctx.user_data["adm_wait"] = {"type": "pnew_group", "data": state["data"]}
                return
            # 使用已选择的发货方式创建商品
            method = state["data"].get("deliver_type")
            if method not in {"join_group", "card_fixed", "card_pool"}:
                # 未选择发货方式，退回选择
                state["type"] = "pnew_wait_deliver"
                ctx.user_data["adm_wait"] = state
                kb = make_markup([
                    [
                        InlineKeyboardButton("👥 自动拉群", callback_data="adm:pnew_set_deliver:join_group"),
                        InlineKeyboardButton("🧷 通用卡密", callback_data="adm:pnew_set_deliver:card_fixed"),
                    ],
                    [InlineKeyboardButton("🔑 卡池", callback_data="adm:pnew_set_deliver:card_pool")],
                    row_home_admin(),
                ])
                await update.message.reply_text("请先选择【发货方式】：", reply_markup=kb)
                return
            name = state["data"].get("name")
            price = state["data"].get("price")
            desc = state["data"].get("desc")
            cover = state["data"].get("cover")
            try:
                cur.execute(
                    "INSERT INTO products(name, price, full_description, cover_url, tg_group_id, deliver_type) VALUES (?,?,?,?,?,?)",
                    (name, price, desc, cover, gid, method),
                )
                conn.commit()
                pid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
            except Exception:
                await update.message.reply_text("保存失败，请稍后重试。")
                return
            ctx.user_data.pop("adm_wait", None)
            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 新商品已创建，正在打开商品页…", ttl=2)
            await _send_product_page(update.effective_chat.id, str(pid))
            return


        # 编辑商品字段
        if kind and kind.startswith("edit_"):
            pid = state["data"].get("pid")
            field = kind.split("_", 1)[1]
            if field == "price":
                try:
                    val = float(text)
                except Exception:
                    pid_back = state["data"].get("pid")
                    kb = make_markup([row_back(f"adm:p:{pid_back}")])
                    await update.message.reply_text("格式不正确，请输入数字价格：", reply_markup=kb)
                    return
            else:
                # 支持直接发图片作为封面
                if field == "cover":
                    photos = getattr(msg, "photo", None)
                    if photos:
                        val = photos[-1].file_id
                        try:
                            await send_ephemeral(update.get_bot(), update.effective_chat.id, "✅ 已收到图片封面，正在保存…", ttl=2)
                        except Exception:
                            pass
                    else:
                        val = text
                else:
                    val = text
            col = {
                "name": "name",
                "price": "price",
                "desc": "full_description",
                "cover": "cover_url",
                "group": "tg_group_id",
                "deliver": "deliver_type",
                "card_fixed": "card_fixed",
            }[field]
            # 若修改群ID，先做强校验，不通过则返回商品页不保存
            if field == "group":
                ok_admin = await _check_and_warn_bot_admin(str(val))
                if not ok_admin:
                    try:
                        await update.message.reply_text("已取消保存。请先将机器人设为该群管理员。")
                    except Exception:
                        pass
                    # 返回单品页面
                    await _send_product_page(update.effective_chat.id, pid)
                    return
            cur.execute(f"UPDATE products SET {col}=? WHERE id=?", (val, pid))
            conn.commit()
            ctx.user_data.pop("adm_wait", None)
            await _send_text(update.effective_chat.id, "✅ 已保存发货方式，返回商品页…", reply_markup=make_markup([row_back(f"adm:p:{pid}")]))
            await _send_text(update.effective_chat.id, "正在刷新…")
            await _send_product_page(update.effective_chat.id, pid)
            return

        # 主页编辑（DB settings）
        if kind and kind.startswith("home_"):
            key = kind.split("_", 1)[1]  # title/intro/cover
            if key == "title":
                _set_setting("home.title", text)
            elif key == "intro":
                _set_setting("home.intro", text)
            elif key == "cover":
                # 支持直接发送图片作为主页封面（保存 file_id），或输入 URL 文本
                val = text
                try:
                    photos = getattr(update.message, "photo", None)
                    if photos:
                        val = photos[-1].file_id
                        try:
                            await update.message.reply_text("✅ 已收到图片封面，正在保存…")
                        except Exception:
                            pass
                except Exception:
                    # 回退到文本
                    pass
                _set_setting("home.cover_url", val)
            ctx.user_data.pop("adm_wait", None)
            m = await update.message.reply_text("✅ 主页设置已更新（已保存到数据库），正在返回主页设置…")
            await asyncio.sleep(1)
            try:
                await update.get_bot().delete_message(update.effective_chat.id, m.message_id)
            except Exception:
                pass
            await _send_home_menu(update.effective_chat.id)
            return

    # 本模块需要用到的去注释 JSON 解析（复用 bot.py 的工具若未提供）
    def _strip_json_comments(s: str) -> str:
        import re as _re
        # 删除 // 和 /* */ 注释
        s = _re.sub(r"/\*.*?\*/", "", s, flags=_re.S)
        s = _re.sub(r"//.*", "", s)
        return s

    # 注册 handlers
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(adm_router, pattern=r"^adm:"))
    # 管理员文本输入（逐步问答）
    # 管理员文本/图片输入（逐步问答）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, adm_text_input))
    app.add_handler(MessageHandler(filters.PHOTO, adm_text_input))

    # 可选：用于自动化测试时导出内部函数引用
    if deps.get("EXPOSE_TEST_HOOKS"):
        return {
            "_send_order_list": _send_order_list,
            "_build_order_toolbar": _build_order_toolbar,
            "_build_order_pagination": _build_order_pagination,
            "adm_router": adm_router,
            "_send_stat_page": _send_stat_page,
        }


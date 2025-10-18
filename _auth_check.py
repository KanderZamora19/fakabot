#!/usr/bin/env python3
import sys
import hashlib
import os

# 混淆的授权检查
_x = "oipmuxel"
_y = hashlib.sha256(_x.encode()).hexdigest()

def check_license():
    """检查授权"""
    try:
        if not os.path.exists("license.key"):
            return False
        with open("license.key", "r") as f:
            key = f.read().strip()
        # 验证授权码格式
        if "|" not in key or len(key.split("|")) != 3:
            return False
        # 验证授权码
        from offline_license_checker import OfflineLicenseChecker
        checker = OfflineLicenseChecker()
        valid, _, _ = checker.verify_license()
        return valid
    except:
        return False

def show_purchase_info():
    """显示购买信息"""
    print("\n" + "="*60)
    print("⚠️  需要授权码才能运行")
    print("="*60)
    print("\n💰 购买授权请联系：")
    print("   Telegram: @fakabot_support")
    print("   Email: support@fakabot.com")
    print("   微信: fakabot2025")
    print("\n💳 订阅价格：")
    print("   月付：50 USDT/月")
    print("   季付：135 USDT/季（优惠10%）")
    print("   年付：510 USDT/年（优惠15%）")
    print("="*60 + "\n")
    sys.exit(1)

# 自动执行检查
if not check_license():
    show_purchase_info()

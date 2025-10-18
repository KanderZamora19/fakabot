#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 授权检查 - 请勿删除此部分，否则程序无法运行
import _auth_check

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线授权验证 - 无需服务器
直接验证授权码，不需要联网
"""

import hashlib
import time
import os
import sys
from datetime import datetime

class OfflineLicenseChecker:
    """离线授权验证器"""
    
    def __init__(self, license_file="license.key"):
        self.license_file = license_file
        # ⚠️ 这个密钥必须和生成器中的密钥一致
        self.SECRET_KEY = "fakabot_2025_secret_key_abc123xyz789def456"
    
    def read_license_key(self):
        """读取授权码"""
        if not os.path.exists(self.license_file):
            return None
        
        try:
            with open(self.license_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取授权文件失败: {e}")
            return None
    
    def verify_license(self):
        """验证授权"""
        license_key = self.read_license_key()
        
        if not license_key:
            return False, "未找到授权文件 license.key", 0
        
        try:
            # 解析授权码
            parts = license_key.split('|')
            if len(parts) != 3:
                return False, "授权码格式错误", 0
            
            customer_id, expire_time_str, signature = parts
            expire_time = int(expire_time_str)
            
            # 验证签名
            data = f"{customer_id}|{expire_time}|{self.SECRET_KEY}"
            expected_signature = hashlib.sha256(data.encode()).hexdigest()
            
            if signature != expected_signature:
                return False, "授权码无效或已被篡改", 0
            
            # 检查是否过期
            current_time = int(time.time())
            if current_time > expire_time:
                expire_date = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d')
                return False, f"授权已过期（过期时间：{expire_date}）", 0
            
            # 计算剩余天数
            days_left = (expire_time - current_time) // 86400
            expire_date = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d')
            
            print(f"\n{'='*60}")
            print(f"✅ 授权验证通过")
            print(f"📝 客户ID: {customer_id}")
            print(f"📅 到期时间: {expire_date}")
            print(f"⏰ 剩余天数: {days_left} 天")
            
            # 快过期提醒
            if days_left <= 7:
                print(f"\n⚠️  授权即将过期！请及时续费")
                print(f"💰 续费联系：")
                print(f"   Telegram: @fakabot_support")
                print(f"   Email: support@fakabot.com")
            
            print(f"{'='*60}\n")
            
            return True, "", days_left
            
        except Exception as e:
            return False, f"授权验证失败: {str(e)}", 0
    
    def check_and_exit(self):
        """检查授权，无效则退出"""
        is_valid, error_msg, days_left = self.verify_license()
        
        if not is_valid:
            print("\n" + "="*60)
            print(error_msg)
            print("="*60)
            print("\n💰 购买或续费订阅请联系：")
            print("   Telegram: @fakabot_support")
            print("   Email: support@fakabot.com")
            print("   微信: fakabot2025")
            print("\n💳 订阅价格：")
            print("   月付：$29/月")
            print("   季付：$79/季（优惠10%）")
            print("   年付：$299/年（优惠15%）")
            print("\n✨ 订阅包含：")
            print("   • 完整功能")
            print("   • 技术支持")
            print("   • 定期更新")
            print("="*60 + "\n")
            sys.exit(1)


# 全局实例
_license_checker = None

def init_license_checker():
    """初始化授权检查器"""
    global _license_checker
    _license_checker = OfflineLicenseChecker()
    _license_checker.check_and_exit()

def get_days_left():
    """获取剩余天数"""
    if _license_checker:
        _, _, days_left = _license_checker.verify_license()
        return days_left
    return 0


# 测试代码
if __name__ == "__main__":
    print("测试离线授权验证...")
    init_license_checker()
    print("✅ 授权验证通过，程序可以正常运行")


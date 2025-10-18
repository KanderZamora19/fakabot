#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 授权检查 - 请勿删除此部分，否则程序无法运行
import _auth_check

#!/usr/bin/env python3
"""
支付页面截图工具
支持真实网页截图和备用二维码生成
"""
import os
import subprocess
import time
from io import BytesIO
from typing import Optional

# 尝试导入Selenium相关模块
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def setup_chrome_driver(headless: bool = True, timeout: int = 30):
    """
    设置Chrome/Chromium WebDriver
    
    Args:
        headless: 是否使用无头模式
        timeout: 页面加载超时时间
    
    Returns:
        WebDriver实例或None
    """
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium不可用，使用备用二维码方案")
        return None
    
    try:
        # Chrome选项配置
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
        
        # 基础配置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 尝试不同的Chrome/Chromium路径
        chrome_paths = [
            '/usr/bin/chromium-browser',   # Alpine Chromium
            '/usr/bin/chromium',           # Debian Chromium
            '/usr/bin/google-chrome',      # Google Chrome
            '/usr/bin/google-chrome-stable',
            'chromium-browser',
            'chromium',
            'google-chrome'
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    chrome_binary = path
                    print(f"✅ 找到浏览器: {path} - {result.stdout.strip()}")
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                continue
        
        if not chrome_binary:
            print("❌ 未找到Chrome/Chromium浏览器，使用备用二维码方案")
            return None
        
        chrome_options.binary_location = chrome_binary
        
        # 尝试使用系统chromedriver或chromium-driver
        driver_paths = [
            '/usr/bin/chromedriver',       # Alpine chromedriver
            '/usr/bin/chromium-chromedriver', # Alpine chromium-chromedriver
            '/usr/bin/chromium-driver',    # Debian chromium-driver
            'chromedriver',
            'chromium-driver'
        ]
        
        driver = None
        for driver_path in driver_paths:
            try:
                if os.path.exists(driver_path) or driver_path in ['chromedriver', 'chromium-driver']:
                    service = Service(driver_path) if os.path.exists(driver_path) else None
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    print(f"✅ 使用驱动: {driver_path}")
                    break
            except Exception as e:
                continue
        
        if not driver:
            # 最后尝试ChromeDriverManager
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✅ 使用ChromeDriverManager")
            except Exception as e:
                print(f"❌ 所有驱动方式都失败: {e}")
                return None
        
        # 设置超时
        driver.set_page_load_timeout(timeout)
        driver.implicitly_wait(10)
        
        return driver
        
    except Exception as e:
        print(f"❌ 浏览器驱动初始化失败: {e}")
        return None


def capture_payment_qr(payment_url: str, timeout: int = 30) -> Optional[BytesIO]:
    """
    截取支付页面的二维码图片
    
    Args:
        payment_url: 支付链接
        timeout: 超时时间（秒）
    
    Returns:
        BytesIO: 图片数据流，失败返回None
    """
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium不可用，跳过真实截图")
        return None
    
    driver = None
    try:
        driver = setup_chrome_driver()
        if not driver:
            return None
        
        print(f"🔧 正在截取支付页面: {payment_url}")
        driver.get(payment_url)
        
        # 等待页面基础加载完成
        wait = WebDriverWait(driver, timeout)
        
        # 1. 等待页面DOM加载完成
        try:
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            print("✅ 页面DOM加载完成")
        except Exception as e:
            print(f"⚠️ 等待DOM加载超时: {e}")
        
        # 2. 等待页面标题加载（确保不是空白页）
        try:
            wait.until(lambda d: d.title and len(d.title.strip()) > 0)
            print(f"✅ 页面标题: {driver.title}")
        except Exception as e:
            print(f"⚠️ 页面标题加载超时: {e}")
        
        # 3. 等待页面body内容出现
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print("✅ 页面内容加载完成")
        except Exception as e:
            print(f"⚠️ 页面内容加载超时: {e}")
        
        # 4. 额外等待确保所有内容加载完成
        time.sleep(5)
        
        # 5. 截取页面中心区域（支付核心部分）
        print("📸 开始截图...")
        
        # 先获取整个页面截图
        screenshot_data = driver.get_screenshot_as_png()
        
        if screenshot_data:
            # 使用PIL裁剪中心区域
            try:
                from PIL import Image
                
                # 将截图数据转换为PIL Image
                full_image = Image.open(BytesIO(screenshot_data))
                width, height = full_image.size
                # 336x375矩形截图 - 左右减7，上面减10，下面加25
                crop_width = 336
                crop_height = 375
                
                print(f"🔍 原始截图尺寸: {width}x{height}")
                
                # 使用测试成功的简单居中策略，往上偏移避开蓝色按钮
                center_x = width // 2
                center_y = height // 2 - 8  # 往上偏移8像素，整体下移15像素
                
                left = center_x - crop_width // 2  # 336/2 = 168
                top = center_y - crop_height // 2  # 375/2 = 187
                right = left + crop_width
                bottom = top + crop_height
                # 边界检查
                if left < 0 or top < 0 or right > width or bottom > height:
                    print('⚠️ 336x375超出边界，使用最大正方形')
                    size = min(width, height)
                    left = (width - size) // 2
                    top = (height - size) // 2
                    right = left + size
                    bottom = top + size
                
                print(f"✅ 居中裁剪336x375: {left},{top} -> {right},{bottom}")
                print(f"✅ 裁剪尺寸: {right-left}x{bottom-top}")
                
                # 裁剪图片
                cropped_image = full_image.crop((left, top, right, bottom))
                
                # 转换回BytesIO
                cropped_buffer = BytesIO()
                cropped_image.save(cropped_buffer, format='PNG')
                cropped_buffer.seek(0)
                
                print(f"✅ 真实截图成功，原始大小: {len(screenshot_data)} bytes")
                print(f"✅ 裁剪后大小: {len(cropped_buffer.getvalue())} bytes")
                print(f"✅ 裁剪区域: 390x390 (以二维码为中心)")
                
                return cropped_buffer
                
            except Exception as e:
                print(f"⚠️ 图片裁剪失败，使用原始截图: {e}")
                screenshot_buffer = BytesIO(screenshot_data)
                return screenshot_buffer
        else:
            print("❌ 截图数据为空")
            return None
        
    except Exception as e:
        print(f"❌ 真实截图失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def capture_payment_qr_fallback(payment_url: str) -> Optional[BytesIO]:
    """
    备用截图方案：使用qrcode生成支付链接二维码
    """
    try:
        import qrcode
        from PIL import Image, ImageDraw, ImageFont
        
        print(f"🔧 开始生成备用二维码，URL: {payment_url}")
        
        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_url)
        qr.make(fit=True)
        
        # 创建二维码图片
        qr_img = qr.make_image(fill_color="black", back_color="white")
        print("✅ 二维码图片生成成功")
        
        # 创建带说明文字的图片
        img_width = 400
        img_height = 500
        img = Image.new('RGB', (img_width, img_height), 'white')
        
        # 粘贴二维码
        qr_img = qr_img.resize((300, 300))
        img.paste(qr_img, (50, 50))
        print("✅ 二维码图片合成成功")
        
        # 添加文字说明
        draw = ImageDraw.Draw(img)
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            try:
                # 尝试其他常见字体路径
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font = ImageFont.load_default()
        
        text = "扫描二维码完成USDT支付"
        try:
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
        except:
            # 兼容旧版PIL
            text_width = len(text) * 10
        
        text_x = (img_width - text_width) // 2
        draw.text((text_x, 380), text, fill="black", font=font)
        print("✅ 文字说明添加成功")
        
        # 保存到BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG', quality=90)
        img_buffer.seek(0)
        
        print(f"✅ 备用二维码生成成功，图片大小: {len(img_buffer.getvalue())} bytes")
        return img_buffer
        
    except Exception as e:
        print(f"❌ 备用二维码生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_payment_screenshot(payment_url: str, use_fallback: bool = True) -> Optional[BytesIO]:
    """
    获取支付页面截图
    
    Args:
        payment_url: 支付链接
        use_fallback: 是否使用备用方案
    
    Returns:
        BytesIO: 图片数据流
    """
    # 优先尝试真实网页截图
    print(f"🔧 尝试真实网页截图: {payment_url}")
    
    # 首先尝试真实截图
    screenshot = capture_payment_qr(payment_url)
    
    if screenshot:
        print("✅ 真实网页截图成功")
        return screenshot
    
    # 真实截图失败时使用备用方案
    if use_fallback:
        print("⚠️ 真实截图失败，使用备用二维码方案")
        return capture_payment_qr_fallback(payment_url)
    
    return None


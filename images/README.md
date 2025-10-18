# 📸 图片说明

## 如何添加图片

### 方法1：使用截图工具

1. 运行机器人
2. 使用 Telegram 截图
3. 保存图片到此目录

### 方法2：使用设计工具

使用 Figma、Canva 等工具设计专业的展示图片。

---

## 需要的图片

### 1. banner.png
- **尺寸**：1200x400 像素
- **内容**：项目 Logo + 标语
- **建议文字**：
  - "Fakabot"
  - "专业的 Telegram 自动发卡机器人"
  - "全自动 | 多支付 | 高性能"

### 2. user-interface.png
- **尺寸**：600x800 像素
- **内容**：用户购买界面截图
- **展示**：
  - 商品列表
  - 商品详情
  - 购买按钮

### 3. payment.png
- **尺寸**：600x800 像素
- **内容**：支付界面截图
- **展示**：
  - 支付方式选择
  - 支付二维码
  - 支付金额

### 4. admin-panel.png
- **尺寸**：600x800 像素
- **内容**：管理后台截图
- **展示**：
  - 数据统计
  - 订单列表
  - 管理菜单

### 5. features.png
- **尺寸**：1000x600 像素
- **内容**：功能特性图
- **展示**：
  - 4种支付方式图标
  - 自动发货流程图
  - 性能优化图表

### 6. auto-delivery.png
- **尺寸**：800x400 像素
- **内容**：自动发货流程图
- **展示**：
  - 支付 → 验证 → 发货 → 完成

---

## 临时方案

如果暂时没有图片，可以：

1. **使用占位图**
   ```
   https://via.placeholder.com/1200x400?text=Fakabot
   ```

2. **使用 Emoji 图标**
   - 在 README 中多使用 Emoji
   - 使用表格和列表美化

3. **使用 Shields.io 徽章**
   ```
   ![License](https://img.shields.io/badge/license-Commercial-blue.svg)
   ```

---

## 图片优化

### 压缩图片

```bash
# 使用 ImageMagick
convert input.png -quality 85 output.png

# 使用在线工具
https://tinypng.com/
```

### 推荐尺寸

- Banner: 1200x400
- 截图: 600x800
- 图标: 128x128
- 流程图: 800x400

---

## 示例图片

你可以使用以下工具创建图片：

1. **Canva** - https://www.canva.com
   - 免费模板
   - 在线编辑
   - 导出 PNG

2. **Figma** - https://www.figma.com
   - 专业设计
   - 协作编辑
   - 免费使用

3. **Excalidraw** - https://excalidraw.com
   - 手绘风格
   - 流程图
   - 简单易用

---

## 快速创建 Banner

### 使用 Canva

1. 访问 https://www.canva.com
2. 搜索 "GitHub Banner"
3. 选择模板
4. 修改文字为 "Fakabot"
5. 下载为 PNG

### 使用代码生成

```python
from PIL import Image, ImageDraw, ImageFont

# 创建图片
img = Image.new('RGB', (1200, 400), color='#0088cc')
draw = ImageDraw.Draw(img)

# 添加文字
font = ImageFont.truetype('Arial.ttf', 60)
draw.text((400, 150), 'Fakabot', fill='white', font=font)

# 保存
img.save('banner.png')
```

---

**注意**：如果暂时没有图片，README 也能正常显示，只是图片位置会显示占位符。

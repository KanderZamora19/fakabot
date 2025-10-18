# 🤖 Fakabot - Professional Telegram Auto-Delivery Bot

[![GitHub release](https://img.shields.io/github/v/release/GUGEGEBAIDU/fakabot?style=flat-square)](https://github.com/GUGEGEBAIDU/fakabot/releases)
[![GitHub stars](https://img.shields.io/github/stars/GUGEGEBAIDU/fakabot?style=flat-square)](https://github.com/GUGEGEBAIDU/fakabot/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/GUGEGEBAIDU/fakabot?style=flat-square)](https://github.com/GUGEGEBAIDU/fakabot/network)
[![GitHub issues](https://img.shields.io/github/issues/GUGEGEBAIDU/fakabot?style=flat-square)](https://github.com/GUGEGEBAIDU/fakabot/issues)
[![License](https://img.shields.io/badge/license-Commercial-blue.svg?style=flat-square)]()
[![Python](https://img.shields.io/badge/python-3.11-blue.svg?style=flat-square)]()
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg?style=flat-square)](https://t.me/sonhshu)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg?style=flat-square)]()

<div align="center">

### 🚀 Automated Delivery System | Multiple Payment Methods | Redis High-Performance Cache

💳 Alipay · WeChat · USDT | 🐳 Docker One-Click Deploy | ⚡ 100x Performance Boost

**Use Cases**: Digital Products · Online Courses · Software Licenses · Memberships

🎬 [Live Demo](https://t.me/fakawan_bot) · 📱 [Contact](https://t.me/sonhshu) · 📖 [Documentation](#-quick-start)

[中文文档](README.md) | English

</div>

---

## ⚠️ Important Notice

This project requires a **license key** to run. The code includes a built-in authorization system that cannot be bypassed.

- ✅ License keys use signature verification and cannot be forged
- ✅ Automatic reminder 7 days before expiration
- ✅ Automatic stop after expiration
- ✅ Support remote renewal without redeployment

---

## ✨ Core Features

### 💳 Payment System

Supports **4 mainstream payment methods**:

| Payment Method | Features | Settlement Speed |
|----------------|----------|------------------|
| **Alipay** | Face-to-face payment, QR code | Real-time |
| **WeChat Pay** | Native payment, QR code | Real-time |
| **USDT (TOKEN188)** | TRC20/ERC20, on-chain verification | 1-3 minutes |
| **USDT (Lemon Pay)** | Multi-chain support, low fees | Seconds |

**Features**:
- ✅ Automatic payment confirmation · ✅ Payment callback handling · ✅ Order status sync · ✅ Payment timeout handling

### 🎯 Auto-Delivery System

**Delivery Methods**:
- 📝 Text content (activation codes, accounts, etc.)
- 🔗 Download links (files, resources, etc.)
- 👥 Group invitations (Telegram groups, channels)

**Features**:
- ⚡ Instant delivery after payment
- 🔄 Automatic retry on failure
- 📊 Delivery record tracking
- 🔒 One-time invitation links (auto-revoke after use)

### ⚡ Performance Optimization

**Redis Cache System**:
- 💾 Product info cache (5 min)
- ⚙️ Config cache (10 min)
- 👤 User session cache (1 hour)
- 📈 100x performance improvement

**Rate Limiting**:
- 🛡️ User payment limit (5 times/5 min)
- 🚫 IP callback limit (100 times/min)
- ⏱️ User command limit (20 times/min)

### 📊 Order Management

**Admin Features**:
- 📋 Order list (all, pending, completed, failed)
- 🔍 Order search (by ID, user, product)
- 📈 Sales statistics (daily, weekly, monthly)
- 💰 Revenue statistics (by product, by payment method)
- 📊 Data export (CSV, Excel)

### 👥 User Management

**User System**:
- 👤 User profiles (ID, username, registration time)
- 📊 Purchase history (order count, total amount)
- 🏷️ User tags (VIP, blacklist, etc.)
- 📝 User notes (remarks, special instructions)

### 🛍️ Product Management

**Product Features**:
- ➕ Add/edit/delete products
- 📦 Inventory management (auto-deduct, low stock alert)
- 💰 Price management (original price, sale price)
- 🎨 Product display (name, description, image)
- 📊 Sales statistics (sales count, revenue)

### 🎨 Admin Panel

**Management Interface**:
- 📊 Dashboard (today's orders, revenue, users)
- 📈 Data charts (sales trends, revenue trends)
- ⚙️ System settings (payment config, notification config)
- 🔔 Message notifications (new orders, payment success)

---

## 🚀 Quick Start

### 🎉 First-Time Setup

> 💡 **For**: First-time deployment after purchasing license

#### Step 1: Clone Project

```bash
git clone https://github.com/GUGEGEBAIDU/fakabot.git
cd fakabot
```

#### Step 2: Configure

```bash
# Copy config example
cp config.json.example config.json

# Edit config
vim config.json
```

**Required fields**:

```json
{
  "BOT_TOKEN": "Your Bot Token",  // Get from @BotFather
  "ADMIN_ID": 123456789,          // Your Telegram ID (from @userinfobot)
  "DOMAIN": "https://yourdomain.com",  // Optional
  "PAYMENTS": {
    // Payment configuration
  }
}
```

**Get Bot Token**:
1. Find [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts to create bot
4. Get Token

**Get Admin ID**:
1. Find [@userinfobot](https://t.me/userinfobot)
2. Send any message
3. Get your ID

#### Step 3: Save License Key (Important!)

```bash
# Paste your complete license key
echo "your_license_key" > license.key

# Example:
echo "M0001|1738310400|abc123def456..." > license.key
```

**Notes**:
- ✅ License key must be complete, no extra spaces or newlines
- ✅ Filename must be `license.key`
- ✅ File location in project root directory

#### Step 4: Start Service

```bash
# Start with Docker Compose
docker-compose up -d
```

#### Step 5: Verify

```bash
# Check logs
docker-compose logs -f

# Should see:
# ============================================================
# ✅ License verified
# 📝 Customer ID: M0001
# 📅 Expiration: 2025-02-17
# ⏰ Days remaining: 30 days
# ============================================================
```

#### Step 6: Test Bot

Search for your bot on Telegram, send `/start`

**If you see welcome message, deployment successful!** 🎉

---

### 🔄 Renewal Guide

> 💡 **For**: License expiring or expired, need renewal

**Important: Renewal only requires replacing license key, all data will be preserved!** ✅

#### Step 1: Contact for Renewal

Contact [@sonhshu](https://t.me/sonhshu), choose renewal plan:

| Plan | Price | Discount |
|------|-------|----------|
| Monthly | 50 USDT | - |
| Quarterly | 135 USDT | 10% |
| Yearly | 510 USDT | 15% |

#### Step 2: Get New License

After payment, you'll receive a file: `renewal_license_M0001_xxx.txt`

File content example:
```
Customer ID: M0001
New License: M0001|1740902400|def456...
Renewal Period: 30 days
New Expiration: 2025-03-19
```

#### Step 3: SSH to Server

```bash
ssh root@your_server_ip
```

#### Step 4: Navigate to Project

```bash
cd fakabot
```

#### Step 5: Replace License

```bash
# Method 1: Direct input
echo "new_license_key" > license.key

# Example:
echo "M0001|1740902400|def456..." > license.key

# Method 2: Use editor
vim license.key
# Delete old license, paste new license, save and exit
```

#### Step 6: Restart Service

```bash
docker-compose restart
```

#### Step 7: Verify Renewal

```bash
# Check logs
docker-compose logs -f

# Should see:
# ============================================================
# ✅ License verified
# 📝 Customer ID: M0001
# 📅 Expiration: 2025-03-19  ← New expiration date
# ⏰ Days remaining: 30 days
# ============================================================
```

**If you see new expiration date, renewal successful!** 🎉

#### ✅ Data Preservation After Renewal

**All data preserved**:
- ✅ All product configurations
- ✅ All order records
- ✅ All customer data
- ✅ config.json settings
- ✅ Database files

**No need to reconfigure anything!** ✅

---

## 💰 Subscription Pricing

### Purchase Options

| Plan | Duration | Price | Discount | Best For |
|------|----------|-------|----------|----------|
| **Monthly** | 30 days | 50 USDT | - | Trial users |
| **Quarterly** | 90 days | 135 USDT | 10% off | Regular users |
| **Yearly** | 365 days | 510 USDT | 15% off | Long-term users |

### How to Purchase

1. **Contact Customer Service**
   - Telegram: [@sonhshu](https://t.me/sonhshu)
   - Provide your requirements

2. **Make Payment**
   - USDT (TRC20): `TDZM5DSSq8SrB8QTSBHyNwrcTswtCjKs9t`
   - Provide transaction hash

3. **Receive License**
   - Get license key file within 5 minutes
   - Includes complete deployment guide

4. **Deploy and Use**
   - Follow documentation to deploy
   - Start earning immediately

---

## 📞 Contact Us

### Customer Service

- **Telegram**: [@sonhshu](https://t.me/sonhshu)
- **Demo Bot**: [@fakawan_bot](https://t.me/fakawan_bot)
- **Response Time**: 24/7 online

### Technical Support

- **GitHub Issues**: [Submit Issue](https://github.com/GUGEGEBAIDU/fakabot/issues)
- **Documentation**: [Complete Documentation](https://github.com/GUGEGEBAIDU/fakabot#readme)

---

## 📄 License

This project is a commercial software and requires a license key to run.

**Copyright © 2025 Fakabot Team. All rights reserved.**

---

<div align="center">

Made with ❤️ by Fakabot Team

[Get Started](#-quick-start) · [View Demo](https://t.me/fakawan_bot) · [Contact](https://t.me/sonhshu)

</div>

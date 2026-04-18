# 质量版本控制系统

四级审批流程的质量文档版本控制系统。

## 功能特性

- 📁 **文档管理** - 上传、版本控制、分类管理
- 🔐 **四级审批** - 部门主管 → 质量负责人 → 分管领导 → 质量总监
- 👥 **用户权限** - 多角色权限管理
- 🔔 **到期提醒** - 文档有效期管理
- 📊 **统计看板** - 文档数量、审批效率一目了然

## 技术栈

- **后端**: Flask + SQLAlchemy
- **数据库**: PostgreSQL (Railway免费提供)
- **前端**: Vue.js 3 + Bootstrap 5
- **文件存储**: 腾讯云 COS（可选）
- **部署**: Railway.app

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写真实配置

# 初始化数据库并启动
python app.py
```

访问 http://localhost:5000

## Railway 部署步骤

### 1. 创建 GitHub 仓库

```bash
cd D:\质量版控系统
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/qc-docs.git
git push -u origin main
```

### 2. 在 Railway 创建项目

1. 访问 https://railway.app
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择你的仓库
4. Railway 会自动检测 Python 项目

### 3. 添加 PostgreSQL 数据库

1. 在项目中点击 "Add Service" → "Database" → "PostgreSQL"
2. Railway 会自动创建数据库并注入 `DATABASE_URL` 环境变量

### 4. 配置环境变量

在 Railway 项目的 Variables 标签添加：

```
SECRET_KEY=你的密钥（随便填一个复杂字符串）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123456
```

### 5. 访问应用

Railway 会自动分配一个域名，类似 `https://xxx-production.up.railway.app`

## 初始账号

部署完成后，系统会自动创建以下账号：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | Admin@123 | 管理员 |
| hanzg | Qc@123 | 一级审批人（韩志刚）|
| wangxl | Qc@123 | 二级审批人（王晓丽）|
| lim | Qc@123 | 三级审批人（李明）|
| zhangzj | Qc@123 | 四级审批人（张总监）|

**⚠️ 部署后请立即修改默认密码！**

## 腾讯云 COS 配置（文件上传）

如需启用真实的文件上传功能：

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/cos)
2. 创建存储桶
3. 获取 SecretId 和 SecretKey
4. 在 Railway 环境变量中添加：

```
COS_SECRET_ID=你的SecretId
COS_SECRET_KEY=你的SecretKey
COS_REGION=ap-guangzhou
COS_BUCKET=你的存储桶名
```

## 目录结构

```
质量版控系统/
├── app.py              # Flask 主程序
├── models.py           # 数据库模型
├── requirements.txt    # Python 依赖
├── Procfile            # Railway 启动命令
├── runtime.txt         # Python 版本
├── .env.example        # 环境变量示例
├── static/
│   └── index.html      # 前端页面
└── README.md           # 本文件
```

## 自定义域名（可选）

在 Railway 项目设置中：
1. 点击 "Settings" → "Domains"
2. 添加你的域名
3. 按提示配置 DNS

---

开发: 小术 🎨

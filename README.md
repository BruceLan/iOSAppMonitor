# Apple 应用监控系统

自动监控 Apple Store 应用上线状态，并通过飞书发送通知。

## 功能特性

- 🔍 自动查询 Apple Store 应用状态
- 📊 从飞书多维表格读取应用信息
- ✅ 智能数据验证（版本号、提审时间）
- � 应用上线后自动发送飞书通知（支持 @ 所有人或指定用用户）
- ⚠️ 数据异常自动预警
- ⏰ 支持定时执行（GitHub Actions）
- 📝 自动更新飞书表格状态

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 环境配置
ENV=local  # 本地调试模式（不发送飞书通知）

# 飞书应用配置（必需）
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_WIKI_URL=your_wiki_url

# 飞书通知配置（生产环境需要，本地调试可不填）
# FEISHU_CHAT_ID_ALL=oc_xxx
# FEISHU_CHAT_ID_TEAM=oc_yyy
# FEISHU_MENTION_USERS=ou_aaa,ou_bbb
```

**环境说明：**
- `ENV=local`：本地调试模式，不发送飞书通知
- `ENV=production`：生产环境，发送飞书通知

### 3. 运行脚本

```bash
python monitor_apple.py
```

## 配置说明

详细配置说明请查看 [CONFIG.md](CONFIG.md)

## 部署指南

GitHub Actions 部署指南请查看 [DEPLOY.md](DEPLOY.md)

## 项目结构

```
apple_monitor/
├── config/                    # 配置管理
│   ├── __init__.py
│   └── settings.py           # 环境变量配置
├── models/                    # 数据模型
│   ├── __init__.py
│   └── record.py             # ApplePackageRecord 数据模型
├── services/                  # 外部服务
│   ├── __init__.py
│   ├── apple_service.py      # Apple Store API 服务
│   ├── feishu_service.py     # 飞书表格服务
│   └── feishu_messenger.py   # 飞书消息服务
├── utils/                     # 工具函数
│   ├── __init__.py
│   ├── logger.py             # 日志工具
│   └── url_parser.py         # URL 解析工具
├── monitor_apple.py          # 主入口（业务流程编排）
├── requirements.txt          # 依赖包
├── .env                      # 环境变量配置
├── CONFIG.md                 # 配置文档
└── DEPLOY.md                 # 部署文档
```

## 数据验证规则

系统会自动验证以下数据完整性：

### 主记录（无子记录）
- ❌ 缺少版本号
- ❌ 缺少提审时间

### 子记录
- ❌ 任何子记录缺少版本号
- ❌ 多条子记录版本号相同
- ❌ 任何子记录缺少提审时间
- ℹ️ 只处理状态为"提审中"或"已发布"的子记录

异常记录会被跳过处理，并发送飞书警告通知（@ 所有人）。

## 权限要求

飞书应用需要以下权限：

- ✅ `bitable:app` - 查看、编辑多维表格
- ✅ `wiki:space` - 访问知识库
- ✅ `im:message` - 发送消息

## 本地开发

### 环境要求

- Python 3.7+
- pip

### 开发流程

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置 `.env` 文件
4. 运行脚本：`python monitor_apple.py`

## 故障排查

### 问题：数据验证失败

查看日志中的"异常记录详情"部分，会显示具体的错误原因和子记录信息。

### 问题：飞书消息发送失败

- 检查应用是否已添加到目标群聊
- 检查应用是否有 `im:message` 权限
- 查看错误码和错误信息

### 问题：表格更新失败

- 检查应用是否有 `bitable:app` 权限
- 检查应用是否已添加为多维表格的协作者

## License

MIT

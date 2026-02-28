# 配置说明

本文档详细说明了 Apple 应用监控系统的所有配置项。

## 环境变量配置

### 必需配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `ENV` | 环境标识 | `local` 或 `production` |
| `FEISHU_APP_ID` | 飞书应用 ID | `cli_a9ccfb2bbf385cc6` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `your_secret_here` |
| `FEISHU_WIKI_URL` | 飞书多维表格 Wiki URL | `https://xxx.feishu.cn/wiki/...` |

**ENV 说明：**
- `local`：本地调试模式，不发送飞书通知，适合开发测试
- `production`：生产环境，发送飞书通知，适合正式运行

### 可选配置（飞书通知）

**注意：** 当 `ENV=local` 时，以下配置不生效（不发送通知）

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `FEISHU_CHAT_ID_ALL` | @所有人的群聊 ID | `oc_1de66c6e3d6dba470e302b2d474db39f` |
| `FEISHU_CHAT_ID_TEAM` | @指定用户的群聊 ID | `oc_26e985ac87884ce23bc1c181cf0f61dc` |
| `FEISHU_MENTION_USERS` | 要 @ 的用户 ID 列表（逗号分隔） | `ou_aaa,ou_bbb,ou_ccc` |

## 配置文件位置

### 本地开发

创建 `.env` 文件在项目根目录：

```bash
# 复制模板
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 本地调试模式（不发送飞书通知）
ENV=local

# 飞书应用配置
FEISHU_APP_ID=cli_a9ccfb2bbf385cc6
FEISHU_APP_SECRET=your_secret_here
FEISHU_WIKI_URL=https://xxx.feishu.cn/wiki/...

# 本地调试时可以不配置通知
# FEISHU_CHAT_ID_ALL=oc_xxx
# FEISHU_CHAT_ID_TEAM=oc_yyy
# FEISHU_MENTION_USERS=ou_aaa,ou_bbb,ou_ccc
```

### GitHub Actions

在 GitHub 仓库中配置 Secrets：

1. 进入仓库 Settings -> Secrets and variables -> Actions
2. 点击 "New repository secret" 添加密钥

**注意：** GitHub Actions 默认为生产环境（`ENV=production`），会发送飞书通知。

## 配置管理（config/settings.py）

配置类 `Settings` 负责加载和管理所有配置：

```python
from config.settings import settings

# 访问配置
app_id = settings.FEISHU_APP_ID
notifications = settings.FEISHU_NOTIFICATIONS

# 验证配置
if settings.validate():
    print("配置有效")
```

### 通知配置结构

`FEISHU_NOTIFICATIONS` 是一个列表，每个元素包含：

```python
{
    "chat_id": "oc_xxx",              # 群聊 ID（必需）
    "mention_all": True,              # 是否 @ 所有人（可选）
    "mention_user_ids": ["ou_xxx"]    # 要 @ 的用户列表（可选）
}
```

## 飞书应用配置

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

### 2. 配置权限

在应用管理页面添加以下权限：

- `bitable:app` - 查看、编辑多维表格
- `wiki:space` - 访问知识库
- `im:message` - 发送消息

### 3. 添加应用到群聊

1. 打开飞书群聊
2. 点击右上角「...」->「设置」
3. 找到「群机器人」->「添加机器人」
4. 搜索并添加你的应用

### 4. 添加应用为多维表格协作者

1. 打开飞书多维表格
2. 点击右上角「...」->「高级设置」或「协作者」
3. 搜索并添加你的应用
4. 确保权限设置为「可编辑」

## 获取群聊 ID 和用户 ID

### 获取群聊 ID

方法 1：通过群设置
1. 打开飞书群聊
2. 点击右上角「...」->「设置」
3. 在 URL 中可以看到群聊 ID（格式：`oc_xxx`）

方法 2：通过开发者工具
1. 使用飞书 API 获取群列表
2. 查找对应群聊的 `chat_id`

### 获取用户 ID

方法 1：通过用户信息
1. 在飞书中打开用户个人资料
2. 使用飞书 API 查询用户信息

方法 2：通过开发者工具
1. 使用飞书 API 获取部门用户列表
2. 查找对应用户的 `open_id`

## 数据验证配置

数据验证规则在 `models/record.py` 的 `validate_data()` 方法中定义。

### 当前验证规则

**主记录（无子记录）：**
- 必须有版本号
- 必须有提审时间

**子记录：**
- 所有子记录必须有版本号
- 不能有重复的版本号
- 所有子记录必须有提审时间
- 只处理状态为"提审中"或"已发布"的子记录

### 自定义验证规则

编辑 `models/record.py` 中的 `validate_data()` 方法：

```python
def validate_data(self) -> Dict[str, Any]:
    errors = []
    
    # 添加自定义验证逻辑
    if self.custom_field is None:
        errors.append("缺少自定义字段")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }
```

## 日志配置

日志工具在 `utils/logger.py` 中定义，支持：

- GitHub Actions 日志分组
- 不同级别的日志（info, warning, error, success）
- 时间戳自动添加

### 使用日志

```python
from utils.logger import log_info, log_warning, log_error, log_success

log_info("信息日志")
log_warning("警告日志")
log_error("错误日志")
log_success("成功日志")
```

## 高级配置

### 修改查询条件

编辑 `monitor_apple.py` 中的查询参数：

```python
records = self.feishu_service.get_records_by_status(
    app_token=app_token,
    table_id=table_id,
    status_field="包状态",      # 修改状态字段名
    target_status="提审中",     # 修改目标状态
    view_id=view_id
)
```

### 修改过滤条件

编辑 `monitor_apple.py` 中的过滤逻辑：

```python
# 过滤出阶段 != "五图" 的所有记录
filtered_records = []
for record in records:
    if record.stage != "五图":  # 修改过滤条件
        filtered_records.append(record)
```

### 修改子记录状态过滤

编辑 `services/feishu_service.py` 中的 `valid_child_statuses`：

```python
valid_child_statuses = ["提审中", "已发布"]  # 添加或删除状态
```

## 故障排查

### 配置验证失败

运行以下命令检查配置：

```python
from config.settings import settings

if settings.validate():
    print("✅ 配置有效")
    print(f"App ID: {settings.FEISHU_APP_ID}")
    print(f"通知配置: {len(settings.FEISHU_NOTIFICATIONS)} 个群")
else:
    print("❌ 配置无效，请检查环境变量")
```

### 权限问题

如果遇到权限错误，检查：

1. 飞书开放平台是否已添加所需权限
2. 应用是否已添加到目标群聊
3. 应用是否已添加为多维表格协作者

### 环境变量未生效

确保：

1. `.env` 文件在项目根目录
2. 环境变量名称正确（区分大小写）
3. 重启应用以加载新的环境变量

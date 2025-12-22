# 配置说明

## 环境变量配置

### 必需的环境变量

| 变量名 | 说明 | 如何获取 |
|--------|------|----------|
| `FEISHU_APP_ID` | 飞书应用 ID | 飞书开放平台 -> 应用详情 -> 凭证与基础信息 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 飞书开放平台 -> 应用详情 -> 凭证与基础信息 |
| `FEISHU_WIKI_URL` | 多维表格 URL | 打开飞书多维表格，复制浏览器地址栏 URL |

### 本地开发配置

1. 复制 `.env.example` 为 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入实际值：
   ```bash
   FEISHU_APP_ID=cli_your_actual_app_id
   FEISHU_APP_SECRET=your_actual_secret
   FEISHU_WIKI_URL=https://your_actual_wiki_url
   ```

3. 使用 python-dotenv 加载环境变量（可选）：
   ```bash
   pip install python-dotenv
   ```

   在代码中添加：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### GitHub Actions 配置

在 GitHub 仓库中配置 Secrets（不要提交到代码仓库）：

1. 进入仓库 **Settings** -> **Secrets and variables** -> **Actions**
2. 点击 **New repository secret**
3. 添加上述三个环境变量

## 通知配置

### 群聊 ID 获取方法

**方法 1：通过飞书开放平台**
1. 打开飞书群聊
2. 点击右上角「...」->「设置」
3. 在群设置中可以看到群 ID

**方法 2：通过 API 获取**
```python
# 使用飞书 SDK 获取群列表
from lark_oapi.api.im.v1 import ListChatRequest

request = ListChatRequest.builder().build()
response = client.im.v1.chat.list(request)
for chat in response.data.items:
    print(f"群名称: {chat.name}, 群ID: {chat.chat_id}")
```

### 用户 open_id 获取方法

**方法 1：通过飞书管理后台**
1. 登录飞书管理后台
2. 进入「通讯录」
3. 找到对应用户，查看详情

**方法 2：通过 API 获取**
```python
# 使用飞书 SDK 获取用户信息
from lark_oapi.api.contact.v3 import GetUserRequest

request = GetUserRequest.builder().user_id("user_id").build()
response = client.contact.v3.user.get(request)
print(f"用户 open_id: {response.data.user.open_id}")
```

### 通知配置示例

编辑 `monitor_apple.py` 中的 `FEISHU_NOTIFICATIONS`：

```python
FEISHU_NOTIFICATIONS = [
    # 配置 1：@ 所有人
    {
        "chat_id": "oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "mention_all": True
    },
    
    # 配置 2：@ 单个用户
    {
        "chat_id": "oc_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "mention_user_ids": ["ou_xxxxxxxxxxxxxxxxxxxxxxxx"]
    },
    
    # 配置 3：@ 多个用户
    {
        "chat_id": "oc_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
        "mention_user_ids": [
            "ou_user1_xxxxxxxxxxxxxxxx",
            "ou_user2_xxxxxxxxxxxxxxxx",
            "ou_user3_xxxxxxxxxxxxxxxx"
        ]
    },
    
    # 配置 4：不 @ 任何人（普通消息）
    {
        "chat_id": "oc_wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww"
    }
]
```

## 安全建议

### ⚠️ 重要：不要泄露敏感信息

1. **永远不要**将以下信息提交到 Git 仓库：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - 群聊 ID
   - 用户 open_id
   - `.env` 文件

2. **使用 .gitignore**
   确保 `.gitignore` 包含：
   ```
   .env
   .env.local
   *.log
   ```

3. **使用 GitHub Secrets**
   - 在 GitHub 上使用 Secrets 存储敏感信息
   - Secrets 不会出现在日志中
   - 只有仓库管理员可以查看

4. **定期更新密钥**
   - 定期在飞书开放平台重置应用密钥
   - 更新 GitHub Secrets 中的值

## 权限配置

### 飞书应用权限

确保应用拥有以下权限：

| 权限 | 权限名称 | 用途 |
|------|---------|------|
| `bitable:app` | 查看、编辑多维表格 | 读取和更新表格数据 |
| `wiki:space` | 访问知识库 | 获取多维表格的 app_token |
| `im:message` | 发送消息 | 发送群聊通知 |

### 添加应用到群聊

1. 打开飞书群聊
2. 点击右上角「...」->「设置」
3. 找到「群机器人」->「添加机器人」
4. 搜索你的应用名称
5. 添加到群聊

### 添加应用到多维表格

1. 打开飞书多维表格
2. 点击右上角「分享」
3. 在「添加协作者」中搜索你的应用
4. 设置权限为「可编辑」

## 故障排查

### 环境变量未设置

**错误信息：**
```
❌ 错误：缺少必要的环境变量
```

**解决方法：**
- 本地运行：检查 `.env` 文件或 `export` 命令
- GitHub Actions：检查 Secrets 配置

### 权限不足

**错误码：91403**
```
❌ 更新失败: Record ID xxx, 错误: 91403, Forbidden
```

**解决方法：**
- 确保应用已添加到多维表格
- 确保应用权限为「可编辑」

**错误码：230002**
```
❌ 飞书消息发送失败, 错误码: 230002
```

**解决方法：**
- 确保应用已添加到目标群聊

### 字段不存在

**错误码：1254045**
```
❌ 更新失败: 错误码: 1254045, FieldNameNotFound
```

**解决方法：**
- 检查字段名称是否正确（"包状态"、"过审时间"）
- 确保多维表格中存在这些字段

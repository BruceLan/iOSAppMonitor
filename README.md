# Apple App Monitor

自动监控 Apple Store 应用上线状态，并发送飞书通知。

## 功能特性

- 🔍 自动查询飞书多维表格中"提审中"的应用
- 📱 通过 iTunes Search API 查询 Apple Store 状态
- ✅ 自动更新飞书表格状态（已发布 + 过审时间）
- 📨 发送飞书群消息通知（支持 @ 所有人 / @ 指定用户）
- ⏰ 每小时自动执行一次（GitHub Actions）

## 部署到 GitHub Actions

### 1. Fork 或上传代码到 GitHub

将代码上传到你的 GitHub 仓库。

### 2. 配置 GitHub Secrets

在 GitHub 仓库中配置以下 Secrets：

1. 进入仓库 Settings -> Secrets and variables -> Actions
2. 点击 "New repository secret" 添加以下密钥：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `FEISHU_APP_ID` | 飞书应用 ID | `cli_xxxxxxxxxxxxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `your_app_secret_here` |
| `FEISHU_WIKI_URL` | 飞书多维表格 URL | `https://xxx.feishu.cn/wiki/...` |

### 3. 启用 GitHub Actions

1. 进入仓库 Actions 标签页
2. 如果提示启用 Workflows，点击启用
3. 工作流会自动每小时执行一次

### 4. 手动触发（可选）

在 Actions 页面，选择 "Apple App Monitor" 工作流，点击 "Run workflow" 可以手动触发执行。

## 配置说明

### 修改执行频率

编辑 `.github/workflows/monitor.yml` 文件中的 cron 表达式：

```yaml
schedule:
  - cron: '0 * * * *'  # 每小时执行
  # - cron: '0 */2 * * *'  # 每 2 小时执行
  # - cron: '0 9-18 * * *'  # 每天 9:00-18:00 每小时执行
```

### 修改通知配置

编辑 `monitor_apple.py` 中的 `FEISHU_NOTIFICATIONS` 配置：

```python
FEISHU_NOTIFICATIONS = [
    {
        "chat_id": "oc_xxx",  # 群聊 ID
        "mention_all": True   # @ 所有人
    },
    {
        "chat_id": "oc_yyy",  # 另一个群
        "mention_user_ids": ["ou_xxx", "ou_yyy"]  # @ 指定用户
    }
]
```

## 本地运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置环境变量

```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
export FEISHU_WIKI_URL="your_wiki_url"
```

### 运行脚本

```bash
python monitor_apple.py
```

## 权限要求

飞书应用需要以下权限：

- ✅ `bitable:app` - 查看、编辑多维表格
- ✅ `wiki:space` - 访问知识库
- ✅ `im:message` - 发送消息

## 注意事项

1. **GitHub Actions 限制**
   - 免费账户每月有 2000 分钟的执行时间
   - 每小时执行一次，每次约 1-2 分钟，完全够用

2. **时区问题**
   - GitHub Actions 使用 UTC 时区
   - 如需调整为北京时间，cron 表达式需要减 8 小时

3. **飞书权限**
   - 确保应用已添加到目标群聊中
   - 确保应用有编辑多维表格的权限

## 查看执行日志

1. 进入 GitHub 仓库的 Actions 页面
2. 点击具体的工作流运行记录
3. 查看详细的执行日志

## 故障排查

### 问题：工作流没有自动执行

- 检查 Actions 是否已启用
- 检查仓库是否有活动（GitHub 可能暂停不活跃仓库的定时任务）

### 问题：执行失败

- 查看 Actions 日志中的错误信息
- 检查 Secrets 是否配置正确
- 检查飞书应用权限是否足够

### 问题：重复通知

- 脚本会检查版本号是否匹配，只有匹配时才通知
- 如果已经更新为"已发布"状态，下次不会再处理

## License

MIT

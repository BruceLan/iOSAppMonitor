# 部署指南

## 快速部署到 GitHub Actions

### 步骤 1：上传代码到 GitHub

```bash
# 初始化 Git 仓库（如果还没有）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Apple App Monitor"

# 关联远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/YOUR_USERNAME/apple-monitor.git

# 推送到 GitHub
git push -u origin main
```

### 步骤 2：配置 GitHub Secrets

1. 打开你的 GitHub 仓库
2. 点击 **Settings** (设置)
3. 左侧菜单选择 **Secrets and variables** -> **Actions**
4. 点击 **New repository secret** 添加以下密钥：

#### 必需的 Secrets：

**FEISHU_APP_ID**
```
cli_xxxxxxxxxxxxxxxx
```
（替换为你的飞书应用 ID）

**FEISHU_APP_SECRET**
```
your_app_secret_here
```
（替换为你的飞书应用密钥）

**FEISHU_WIKI_URL**
```
https://xxx.feishu.cn/wiki/xxxxxx?table=xxxxx&view=xxxxx
```
（替换为你的飞书多维表格 URL）

### 步骤 3：启用 GitHub Actions

1. 点击仓库顶部的 **Actions** 标签
2. 如果看到提示，点击 **I understand my workflows, go ahead and enable them**
3. 你会看到 "Apple App Monitor" 工作流

### 步骤 4：测试运行

#### 方式 1：手动触发
1. 在 Actions 页面，点击左侧的 "Apple App Monitor"
2. 点击右侧的 **Run workflow** 按钮
3. 点击绿色的 **Run workflow** 确认
4. 等待几秒，刷新页面查看执行结果

#### 方式 2：等待自动执行
- 工作流会在每小时的第 0 分钟自动执行
- 例如：10:00, 11:00, 12:00...

### 步骤 5：查看执行日志

1. 在 Actions 页面，点击具体的工作流运行记录
2. 点击 "monitor" 任务
3. 展开各个步骤查看详细日志

## 自定义配置

### 修改执行频率

编辑 `.github/workflows/monitor.yml`：

```yaml
schedule:
  # 每小时执行
  - cron: '0 * * * *'
  
  # 每 2 小时执行
  # - cron: '0 */2 * * *'
  
  # 每天 9:00-18:00 每小时执行
  # - cron: '0 9-18 * * *'
  
  # 每天 10:00 执行
  # - cron: '0 10 * * *'
```

**注意：** GitHub Actions 使用 UTC 时区，北京时间需要减 8 小时。
- 北京时间 10:00 = UTC 02:00 → `cron: '0 2 * * *'`

### 修改通知群组

编辑 `monitor_apple.py` 中的配置：

```python
FEISHU_NOTIFICATIONS = [
    {
        "chat_id": "oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "mention_all": True  # @ 所有人
    },
    {
        "chat_id": "oc_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "mention_user_ids": [
            "ou_xxxxxxxxxxxxxxxxxxxxxxxx",
            # 添加更多用户 ID
        ]
    }
]
```

提交修改：
```bash
git add .
git commit -m "Update notification config"
git push
```

## 常见问题

### Q: 为什么工作流没有自动执行？

A: 可能的原因：
1. Actions 未启用 - 检查 Actions 页面
2. 仓库不活跃 - GitHub 可能暂停不活跃仓库的定时任务
3. 刚推送代码 - 等待下一个整点

### Q: 如何查看是否执行成功？

A: 
1. 进入 Actions 页面
2. 查看最近的运行记录
3. 绿色勾号 = 成功，红色叉号 = 失败

### Q: 执行失败怎么办？

A:
1. 点击失败的运行记录
2. 查看详细日志
3. 常见错误：
   - Secrets 配置错误
   - 飞书权限不足
   - 网络问题

### Q: 如何停止自动执行？

A:
1. 进入 Actions 页面
2. 点击左侧的 "Apple App Monitor"
3. 点击右上角的 "..." -> "Disable workflow"

### Q: 会不会重复通知？

A: 不会。脚本只会在以下情况发送通知：
- 飞书表格中状态为"提审中"
- Apple Store 版本号与表格中最新版本匹配
- 更新状态后，下次不会再处理该应用

## 成本说明

GitHub Actions 免费额度：
- 公开仓库：无限制
- 私有仓库：每月 2000 分钟

每小时执行一次，每次约 1-2 分钟：
- 每天：24 次 × 2 分钟 = 48 分钟
- 每月：48 × 30 = 1440 分钟

**完全在免费额度内！**

## 安全建议

1. ✅ 使用 GitHub Secrets 存储敏感信息
2. ✅ 不要在代码中硬编码密钥
3. ✅ 定期更新飞书应用密钥
4. ✅ 限制飞书应用权限范围

## 下一步

- [ ] 添加错误通知（执行失败时发送飞书消息）
- [ ] 添加执行统计（每天处理了多少应用）
- [ ] 支持多个多维表格
- [ ] 添加 Web 界面查看执行历史

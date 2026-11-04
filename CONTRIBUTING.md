# 参与和维护

修复问题可使用 `fix/简短名称` 分支，新功能使用 `feat/简短名称` 分支。修改后运行 `python -m unittest discover -v`，
通过 PR 合并到 main。PR 写清触发条件、修改行为、验证结果；界面或动作修改附预览。
不要提交真实 settings.json、认证文件、聊天数据库和日志；新增素材必须说明来源及适用许可。

## 发布下一版

1. 修改 VERSION（例如 0.1.2）并在 CHANGELOG.md 记录本版变化。
2. 运行测试并合并到 main，确认 Checks 工作流通过。
3. 执行：

```powershell
git switch main
git pull --ff-only
git tag -a v0.1.2 -m "Release 0.1.2"
git push origin v0.1.2
```

Release 工作流验证标签与 VERSION 一致，运行测试，再发布源码运行包及校验文件。
不要重写已发布的版本标签。小修复增加补丁号（0.1.2），新增功能可用 0.2.0；不兼容变更需在更新记录中明确说明。

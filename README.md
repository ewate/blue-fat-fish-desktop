# 蓝色大肥鱼 · Windows 桌宠

[![Checks](https://github.com/ewate/blue-fat-fish-desktop/actions/workflows/checks.yml/badge.svg)](https://github.com/ewate/blue-fat-fish-desktop/actions/workflows/checks.yml)
[![Release](https://img.shields.io/github/v/release/ewate/blue-fat-fish-desktop)](https://github.com/ewate/blue-fat-fish-desktop/releases)

一个蓝白配色的独立 Windows 桌宠。点击互动，拖动陪伴；状态、消息和额度卡片可以分别展开或隐藏。

![桌宠预览](docs/preview.jpg)

**[下载最新源码运行包](https://github.com/ewate/blue-fat-fish-desktop/releases/latest)** · **[1080p 演示视频](https://github.com/ewate/blue-fat-fish-desktop/releases/download/v0.1.0/blue-fat-fish-demo-1080p.mp4)**

## 功能

- 连续摆头、独立计时的随机单眨/双眨；尾巴同时左右和上下轻摆。
- 吃白饭、举手挥动、开心摇摆、抛媚眼、闭眼侧头笑。
- 60 FPS 渲染目标与短姿势过渡，实际帧率取决于电脑负载。
- 无边框蓝白圆角菜单、会话选择器、消息卡片、额度卡片和状态胶囊。
- 大小 96～320 像素，动画速度 0.5～2.0 倍；位置、速度及开关自动保存。
- 可选连接本机 Codex，显示最近一轮状态、最新助手回复及账号额度。

## 运行

Windows 10/11，Python 3.10～3.12（带 Tk）。在自己选择的 Python 环境中执行：

```powershell
git clone https://github.com/ewate/blue-fat-fish-desktop.git
cd blue-fat-fish-desktop
python -m pip install -r requirements.txt
python pet.py
```

也可以下载 Release 的源码运行包，解压后安装依赖并双击 `launch.bat`。
如需指定解释器，设置 `PET_PYTHON` 为该解释器的完整路径。当前发布包不是免安装 EXE。

## 操作

| 操作 | 效果 |
|---|---|
| 单击人物 | 随机播放动作 |
| 按住人物拖动 | 移动桌宠与附属卡片 |
| 右键人物 | 菜单、指定动作、模块开关、大小与速度 |
| 单击状态条 | 显示或隐藏消息 |
| 卡片右上角 × | 收起当前模块；右键人物可恢复 |
| 速度滑块 | 即时改变播放速度，松手保存 |

## Codex 同步与隐私

默认关闭。右键“连接 Codex 同步”后，选择本机要跟随的会话；需要运行者自己安装并登录 Codex。
不需要提交 API key，也不附带作者的账号、聊天、额度或登录文件。

- 每 2 秒只读 Codex 本地历史数据库中的状态和最新助手消息。
- 每 30 秒通过本机 `codex app-server` 查询账号额度；可能与桌面端有短暂刷新差异。
- 不将聊天上传到项目服务器，不读取或展示内部推理。
- 本机数据库表名、安装位置可能随 Codex 升级变化；此适配并非稳定的官方接口承诺。
- `settings.json`、`pet.log`、数据库和认证文件不应提交到仓库，已配置忽略规则。

视频为动画及功能界面演示，消息与额度使用示例数据。

## 素材与许可证

**程序代码采用 MIT；角色素材许可与代码分开。** 动画是参考用户提供形象绘制的 AI 辅助衍生素材，
不主张原型角色设计或第三方权利，也不以 MIT 对这些原始权利作额外授权。详见 [ASSET_NOTICE.txt](ASSET_NOTICE.txt)。
项目未复制参考表情仓库的 GIF。原始参考图、个人会话和认证数据均不包含在发布中。

如需使用独立的程序化蓝鲸示例，可先备份 `assets`，再运行 `python make_sample_assets.py`。
已提供本轮使用的生成精灵图与构建脚本，可运行 `python build_assets.py`、`python smooth_animation.py` 重新构建动画帧。
原始用户参考图和过时收碗素材未纳入仓库。

自有 PNG 素材按 `assets/animations-smooth.json` 替换；路径相对 `assets`，图像使用 RGBA。

## 开发和后续版本

```powershell
python -m unittest discover -v
python tools/build_release.py
```

提交和 PR 会运行 Windows / Python 3.10、3.12 自动检查。准备新版本时修改 `VERSION` 与 `CHANGELOG.md`，
提交到 `main` 后推送匹配的 `vX.Y.Z` 标签。Release 工作流会先测试，再打包、计算 SHA-256 并发布下载文件。
完整操作见 [CONTRIBUTING.md](CONTRIBUTING.md)。

欢迎通过 [Issues](https://github.com/ewate/blue-fat-fish-desktop/issues) 反馈问题和建议。
此项目含 AI 辅助代码与素材，是非官方项目，无 OpenAI、Codex 或 DeepSeek 背书。

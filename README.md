# NexusFlow Skills · 智能体技能库

面向 NexusFlow 平台的开源 AI 智能体技能库，遵循 Agent Skills 标准，帮助用户在自己的 AI 智能体客户端中使用平台功能、完成任务并自动化工作流程。

本仓库默认使用**简体中文**，包括使用文档、贡献说明和技能说明。技术标识、标准字段、命令和文件名保留原文。

**当前状态：已收录 2 个迁移技能，已完成结构检查和离线合成测试；尚未发布正式安装包，平台端迁移与求解兼容性未验证。**

## 技能目录

| 技能 | 用途 | 工具范围 |
| --- | --- | --- |
| [SPS → NexusFlow](skills/sps-to-nexusflow/SKILL.md) | SPS 气体管网迁移、单位与组分转换、曲线和拓扑核查 | 离线辅助工具，不是完整 SPS 解释器 |
| [SynergiGas → NexusFlow](skills/synergigas-to-nexusflow/SKILL.md) | MDB 模型迁移、边界及拓扑审计、稳态与瞬态校验 | 离线结构检查，不是通用 MDB 转换器 |

技能不附带实际工程案例或平台凭据。文档与测试中的数据为明确标注的合成示例，详见 [入库检查记录](docs/reviews/2026-09-24-migration-skills.md)。每个技能以 `SKILL.md` 为入口。

## 目录结构

```text
nexusflow-skills/
├── skills/                 # 可独立安装的迁移技能
├── docs/                   # 安装、编写、兼容性和发布说明
├── scripts/                # 校验与打包工具
├── tests/                  # 工具测试；后续加入技能场景测试
├── .github/                # 自动检查、发布流程、问题和贡献模板
├── VERSION                 # 整个技能集合的统一版本
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

## 使用与维护

- 用户安装：[安装指南](docs/installation.md)
- 技能编写：[编写规范](docs/authoring.md)
- 客户端和平台支持：[兼容性记录](docs/compatibility.md)
- 社区贡献：[贡献指南](CONTRIBUTING.md)
- 维护者发布：[发布流程](docs/releasing.md)

维护工具需要 Python 3.11 或更新版本：

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
```

Windows 上也可以使用 `py -3` 替代 `python`。这些依赖属于仓库维护工具，不代表每个技能都要求用户安装 Python。

## 设计约定

- 遵循 [Agent Skills 规范](https://agentskills.io/specification)，技能源码只维护一份。
- 每个技能能够单独下载；所需静态资源放在自己的目录内。
- SDK、MCP、客户端插件按需求接入，并在技能中说明前置条件。
- 平台地址和用户凭据由使用者配置，不随技能分发。
- 仅公布实际验证过的兼容范围；技能格式可读不等于所有工具都可运行。
- 普通用户使用正式版本；私有部署用户可以固定版本，升级前查看兼容记录。

## 许可证

本仓库采用 [MIT 许可证](LICENSE)，许可证文件保留英文原文。第三方材料如有不同许可，须在所属技能内保留相应声明。

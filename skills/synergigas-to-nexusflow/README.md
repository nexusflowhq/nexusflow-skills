# synergigas-to-nexusflow

通用的气体管网模型迁移 agent skill。入口为 [SKILL.md](SKILL.md)。文档与代码按 MIT 许可提供；不隶属于或代表 SynergiGas、NexusFlow 的供应商。

将整个文件夹放入支持 SKILL.md 的 agent 技能目录，或在 Codex 中放入用户 skills 目录。重新载入技能后，用 `$synergigas-to-nexusflow` 发起模型迁移任务。

附带 Python 3.10+ 标准库离线结构检查与合成测试。实际 MDB 读取需要可用读取驱动；实际平台适配需要目标版本的组件结构和授权访问。此包不包含通用转换器、厂商 SDK 或自动部署客户端。

```sh
python -m unittest discover -s tests -v
python scripts/audit_model.py /path/to/private/normalized.json
```

公开包只含通用说明及合成测试。请把运行输入、输出、参考数据、模型快照和凭据保存在包外。提交问题时使用最小合成复现，不上传实际管网或访问秘密。

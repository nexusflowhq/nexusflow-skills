# 安装指南

当前已收录 `sps-to-nexusflow` 和 `synergigas-to-nexusflow`，尚未发布正式安装包。可以从本地仓库复制完整技能目录，按客户端文档安装；公开发布后的下载方式如下。

## 从正式版本下载

1. 在仓库 Releases 中选取与平台版本兼容的正式版本。
2. 下载单技能 ZIP 或完整技能集合，必要时对照 `SHA256SUMS.txt` 核验下载文件。
3. 解压后，按客户端文档将整个技能文件夹导入或放到技能目录；保留 `SKILL.md` 和配套资源的相对位置。
4. 按技能要求配置平台地址、用户认证及 SDK/MCP 等依赖。
5. 使用技能页面提供的示例任务确认安装成功。

完整包用于批量解压和选择技能；不能假定所有客户端都能直接导入一个包含多个技能的 ZIP。
单技能 ZIP 内只有一个顶层技能目录，其中包含许可证。

## 使用通用安装工具

可选用 [Vercel skills CLI](https://github.com/vercel-labs/skills)。仓库发布后，将下列 `YOUR_ORG` 换成真实组织名，技能名换成实际名称：

```bash
npx skills add YOUR_ORG/nexusflow-skills --list
npx skills add YOUR_ORG/nexusflow-skills --skill sps-to-nexusflow -a codex
```

该示例尚不可直接使用。安装范围、其他客户端和升级操作以安装工具的当前文档为准。

## 更新与回退

升级前查看更新记录和兼容性记录。需要可复现部署时保留正式版本 ZIP 和校验文件，记录已安装版本。
不要把凭据或个人定制写入已安装的技能文件。回退时恢复此前的技能目录，并重新确认所需 SDK/MCP 版本。

客户端原生插件尚未提供；未来从同一套技能源码生成。

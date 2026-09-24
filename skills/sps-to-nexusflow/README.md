# SPS → NexusFlow 迁移技能

用于将 SPS 气体管网算例迁移到 NexusFlow 的智能体技能，结合离线辅助工具，保留单位、拓扑、气体组分及压缩机曲线的转换依据，明确稳态和瞬态的验证边界。

将转换经验整理为可执行的智能体工作流程，避免把稳态、指定时刻边界稳态和定工况等效混为一谈。核心入口为 [SKILL.md](SKILL.md)。

## 安装与调用

将整个 `sps-to-nexusflow` 文件夹放入客户端支持的技能目录，按客户端要求重新加载。具体安装位置以所用客户端文档为准；没有技能安装机制时也可直接阅读入口文件。

调用示例：

> 使用 $sps-to-nexusflow 将我提供的 SPS 气体管网算例转换为 NexusFlow 模型，先检查当前接口能力，保留原模型和转换依据，再计算并验证。

> 使用 $sps-to-nexusflow 提取经过指定天数的边界条件建立稳态对照，区分原设备性能图模型与定工况等效模型。

无网络连接时可完成离线工作。平台导入、运行及保存依赖当前可用且获授权的 NexusFlow 工具；技能不绑定某个服务器或 MCP 宿主工具名称。

## 工具及验证

辅助脚本只需 Python 3.10+ 标准库，不访问网络，不自带认证客户端或第三方求解器：

```
python -B scripts/test_conversion_tools.py
python scripts/conversion_tools.py --help
```

输入样例和支持范围见 [references/helpers.md](references/helpers.md)。这些工具处理组分换算、冻结参考曲线、有限 RAMP 子集、时间插值与端口拓扑；不是完整SPS解析器，也不是一键生成任意NexusFlow版本模型的程序。

测试全部使用独立合成数据。完整模型迁移仍需实际源文件、版本依据、实时平台schema及结果验收；合成测试通过不代表任意工程算例可收敛。

## 许可证与适用范围

本技能的说明和辅助代码采用 [MIT 许可证](LICENSE)。SPS 和 NexusFlow 名称用于说明互操作目标，不表示原技能包获得相关产品厂商背书。包内不包含第三方软件、手册、实际模型数据或凭据，也不对这些材料重新授权；使用者需要自行取得有权使用的工具和数据。

发布准备见 [references/publishing.md](references/publishing.md)。生成发布包不等于已经公开发布。

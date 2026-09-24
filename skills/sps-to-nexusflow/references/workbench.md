# MCP、令牌和可恢复工作流

优先使用已连接的 NexusFlow 工具。配对JSON可能带 Markdown URL 和下划线转义，仅规范明确的格式，不猜地址或修改令牌字符。

## 凭据生命周期

- 页面码可能只可成功兑换一次。通过运行时安全输入交给长期存活进程；不写入技能、命令行参数、仓库、日志、异常详情或发布包。
- 成功后仅在内存保存访问令牌、最新刷新令牌和到期时间。不输出整个认证响应；可输出剩余有效秒数。
- 超时导致兑换结果不明时，不自动重兑单次码；使用服务端确认途径或新配对。
- 临近到期或401时按服务端契约刷新，使用锁串行刷新并立即替换两种令牌。旧刷新令牌可能立即失效。
- invalid_grant/连接失效时停止认证重试并请求新配对；继续可做的离线分析。不要重启唯一保存凭据的进程。
- 凭据仅发往配对授权资源和令牌端点，不跟随跨源重定向发送 Authorization，不试投其他 REST 路由。
- 任务完成或用户断开后释放内存；断线不证明草稿已恢复或已保存。

本技能不附带网络认证客户端，以免假定认证版本、运行环境和进程生命周期。

## 动态发现与修改

读取宿主发现结果或 tools/list，确认真实输入 schema。常见入口：

| 用途 | 常见工具 |
|---|---|
| 页面和修订 | workbench_get_context |
| 元件定义 | workbench_component_catalog / component_schema |
| 草稿 | workbench_model_inspect / model_query_components |
| 修改/校验/撤销 | workbench_model_apply_operations / model_validate / model_history |
| 计算 | workbench_simulation_start / simulation_get / simulation_control |
| 结果 | workbench_results_catalog / results_query |
| 展示/导出 | workbench_focus / capture_view / model_export |

确认参数单位、choice值、表格列顺序和容量。`class_id=global` 未必有效，全局定义从实际公开入口或界面读取，不以报错为由猜字段。

备份快照后生成语义操作，稳定ID与标签分开。修改带最新 expected_revision；撤销后修订号可能回退，后续不一定连续。若用户编辑了草稿，先比较再决定如何恢复。批量上限来自当前接口，不硬编码历史值。

参数验证成功不等于计算收敛。启动前保存输入和哈希，按返回任务ID读取结果。确认任务快照独立保存后，才可提交诊断即撤回草稿；不清楚隔离语义时保留诊断输入直到任务结束或使用平台独立模型机制。

## 结果及保存

历史结果查询曾采用 `selector.type` 单数，误传 `types` 可能被忽略。必须检查返回 key/type，按 cursor 分页，按设备或变量分块尊重点数/单元格限制。缺失结果不是零。

稳态图可能保存 log10 残差，需要还原到残差尺度。update/append 结果按实际语义合并，不能只取第一条。保留单位及列编码。

分别核实草稿修改、导出、任务成功和数据库保存。若接口不支持保存，且没有可用授权UI/API，告知用户需手动保存；成功任务和本地JSON不证明页面已经持久化。不猜测保存路由。

# 离线校验契约

`audit_model.py` 接受物理中间图，不接受 NexusFlow 原始 payload。适配器负责从源模型生成此结构。单位已归一：压力 MPa，管长 m，内径/粗糙度 mm；流量在全模型一致地采用 kg/s 或明确标准条件下的 m³/h。流量正负约定由适配器声明并检查，脚本不转换单位。

最小合成样例：

```json
{
  "pressure_basis": "absolute",
  "flow_basis": "mass",
  "start": "2000-01-01T00:00:00+00:00",
  "end": "2000-01-01T00:10:00+00:00",
  "nodes": [{"id": "n1"}, {"id": "n2"}],
  "elements": [{"id": "p1", "kind": "pipe", "from": "n1", "to": "n2", "status": "open", "length_m": 100, "inner_diameter_mm": 80, "roughness_mm": 0.01}],
  "boundaries": [
    {"id": "b1", "node": "n1", "type": "pressure", "series": [["2000-01-01T00:00:00+00:00", 0.6], ["2000-01-01T00:10:00+00:00", 0.6]]},
    {"id": "b2", "node": "n2", "type": "flow", "zero_all_times": true, "series": [["2000-01-01T00:00:00+00:00", 0], ["2000-01-01T00:10:00+00:00", 0]]}
  ]
}
```

`flow_basis=standard_volume` 还需 `standard_conditions` 对象，含正数 `temperature_K`、`pressure_Pa_abs`、`Z`。时间统一使用同一时区；稳态 start=end。常数边界也展开至区间两端；实际目标格式可由适配器压缩。曲线时间需先按原定义展开，工具不自动插值。

验证范围：ID、端点、关闭切分、管道基础几何、边界类型、曲线次序/覆盖/有限数值和全时段零流量。多定压源不会自动报错。没有定压锚点提示 warning，需人工判断瞬态封闭区。

不验证：厂商枚举、气质、热物性、端口协议、调压器控制、模型可解性、流量守恒或求解结果。`valid=true` 仅表示上述结构检查通过，不代表算例等价或可收敛。错误报告可能包含运行时模型 ID，属于私有输出。

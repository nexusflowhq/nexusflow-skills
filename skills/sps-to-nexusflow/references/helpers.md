# 辅助工具契约

Python 3.10+，仅标准库，无网络和第三方求解器。以下命令在技能目录运行；把输入与输出放在项目工作目录，避免发布时混入数据。

```
python scripts/conversion_tools.py gas input.json --output new-output.json
python scripts/conversion_tools.py curve input.json --output new-output.json
python scripts/conversion_tools.py ramps case.intran --output ramps.json
python scripts/conversion_tools.py ramp-gas input.json --output sampled-gas.json
python scripts/conversion_tools.py sample input.json --output reference.json
python scripts/conversion_tools.py topology input.json --output topology-audit.json
python -B scripts/test_conversion_tools.py
```

工具不覆盖已有输出。退出码0表示请求的数据处理成功，不表示工程验收或平台运行成功；1为输入/路径错误；2表示拓扑错误或离散状态未决。省略 --output 时向标准输出写JSON；其中可能含工程数据，不放入公共日志。

所有输入采用UTF-8 JSON（ramps 输入为文本），数值必须有限，重复JSON键会被拒绝。输出不是 NexusFlow 可运行模型；需要根据实时schema再生成操作或模型文件。单位换算由调用者明确完成，工具不会识别任意单位文本。

## gas

合成示例，分子量是测试用取整值，不能当作生产物性库：

```json
{"components":[
  {"name":"A","mass_weight":50,"molecular_weight":16},
  {"name":"B","mass_weight":50,"molecular_weight":28}
]}
```

name 使用核实后的目标组分名称。每个 mass_weight 使用同一尺度，分子量全部采用一致单位。输出 mole_fraction 和 mole_percent 两种数组。

## curve

```json
{"reference":{"n_poly":1.3,"head_m":1000,"absolute_ratio":1.2,"provenance":"synthetic fixture"},
 "head_efficiency_flow_speed":[[1000,80,200,3000],[800,80,300,3000]]}
```

每行是扬程m、多变效率百分数、入口实际流量m³/h、rpm。仅实现 compressors.md 中的冻结常指数近似。输出附近似标识、参考信息、速度线点数。至少每速度线2点不意味着满足完整运行区，应另核实喘振/堵塞边界。

## ramps

只支持显式数值列表及 REPEAT=NO 的 RAMP 子集，支持行首加号续行、数值列表逗号和科学记数法。示例：

```text
RAMP FEED_A:SN2=1
+ 2
+ TIME=10
+ 20
+ REPEAT=NO
```

不解析其余指令、隐式初值、算术表达式、重复或宏，遇不支持的 RAMP 报错。`/*` 在此子集中按行尾注释处理，不支持块注释语法。返回 EXPLICIT_RAMPS_ONLY，不能以此替代完整 INTRAN 审计。时间和数值的单位仍需从源文件独立核查。

## ramp-gas

```json
{"components":[{"name":"A","mass_weight":50,"molecular_weight":16},
               {"name":"B","mass_weight":50,"molecular_weight":28}],
 "semantics":"linear_raw_mass_weights_then_normalize",
 "initial_time_min":0,"after_last":"hold",
 "ramps":{"B":[[100,150]]},"times_min":[0,50,100,200]}
```

显式节点必须严格晚于初始时刻，初值取 components 中的原权重。未指定 ramp 的分量保持原权重；指定分量逐次插值后再归一和转摩尔。after_last 必须是 hold 或 error。只有在验证该语义与实际SPS版本一致后才用此模式。

## sample

```json
{"continuous":["pressure_MPag"],"discrete":["state"],"time_min":5,
 "series":[{"time_min":0,"values":{"pressure_MPag":2,"state":"On"}},
           {"time_min":10,"values":{"pressure_MPag":4,"state":"On"}}]}
```

每行必须恰好包含声明的变量，时间严格递增。连续量线性插值；离散量两侧相同才取值，否则标 null、输出 unresolved_states 并返回退出码2。不会外推。两端状态相同不能证明中间没有动作，仍需独立事件审计。离散阀位若代表真实连续阀杆行程，需基于物理意义重新分类，不能凭字段名决定。

## topology

```json
{"source_nodes":["N1","N2"],
 "ports":[{"port":["feed","0"],"source_node":"N1"},
          {"port":["pipe","0"],"source_node":"N1"},
          {"port":["pipe","1"],"source_node":"N2"}],
 "connections":[{"from":["feed","0"],"to":["pipe","0"]}]}
```

连接边来自平台实际连接；ports 必须覆盖所有实际流体端口。内部设备两端不是连接边，否则会错误短接其上下游物理节点。工具检测源节点短接、拆分、未映射节点、未知端口及自连；不验证端口方向、额外漏报端口或水力物理。

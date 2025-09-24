## 一、更新源 

baseurl根据机器架构进行调整x86_64还是aarch64。**930发布之后无需更新源**，安装只支持openeuler24.03sp2

```
echo "[SHELL]
name=SHELL
baseurl=https://eulermaker.compass-ci.openeuler.openatom.cn/api/ems4/repositories/openEuler-24.03-LTS-SP2:epol/openEuler%3A24.03-LTS-SP2/x86_64/
enabled=1
gpgcheck=0
sslverify=0
gpgkey=http://repo.openeuler.org/openEuler-24.03-LTS-SP2/OS//RPM-GPG-KEY-openEuler">>/etc/yum.repos.d/shell.repo

```

## 二、安装openeuler-intelligence-cli和openeuler-intelligence-installer

~~~bash
dnf install openeuler-intelligence-cli openeuler-intelligence-installer -y
~~~

![image-20250918092746531](./img/image-20250918092746531.png)

## 三、初始化openeuler-intelligence

~~~bash
oi --init
~~~

![image-20250918092914434](./img/image-20250918092914434.png)

特别说明：shell客户端的界面会随着终端的适配情况出现不同的样式，是正常现象，本文档以windows10的cmd终端为例进行展示。

### 3.1 选择部署新服务

![image-20250918092956884](./img/image-20250918092956884.png)

### 3.2 点击继续配置

![image-20250918093033417](./img/image-20250918093033417.png)

### 3.3 服务器ip默认127.0.0.1，部署模式选择默认的轻量部署，点击LLM配置

![image-20250918093329139](./img/image-20250918093329139.png)

### 3.3 依次填写API端点、API秘钥、模型名称，轻量部署可不填写Embedding配置，全量部署需要填写。

![image-20250918093620039](./img/image-20250918093620039.png)

### 3.4 点击开始部署，等待部署执行完成

![image-20250918095405109](./img/image-20250918095405109.png)

![image-20250918095742768](./img/image-20250918095742768.png)

![image-20250918100010161](./img/image-20250918100010161.png)3.5点击完成，结束openeuler-intelligence初始化

## 四、shell客户端的使用

具体参考euler-copilot-shell仓说明文档

链接：[README.md · openEuler/euler-copilot-shell - 码云 - 开源中国](https://gitee.com/openeuler/euler-copilot-shell/blob/dev/README.md#使用方法)

### 4.1 打开shell客户端

~~~bash
oi
~~~

![image-20250918100409132](./img/image-20250918100409132.png)

### 4.2 选择智能体，默认为hce运维助手

![image-20250918100502872](./img/image-20250918100502872.png)

### 4.3 进行智能体的使用，此处以hce运维助手举例，回车确认，进入对话界面

![image-20250918100635136](./img/image-20250918100635136.png)

### 4.4 在左下角输入栏输入命令或问题，如帮我分析当前机器性能情况，智能体会根据提问选择合适的mcp工具，并询问是否执行，此处点击确认

![image-20250918100832293](./img/image-20250918100832293.png)

### 4.5 根据具体情况依次执行mcp工具

![image-20250918101004733](./img/image-20250918101004733.png)

![image-20250918101029066](./img/image-20250918101029066.png)

![image-20250918101147653](./img/image-20250918101147653.png)

### 4.6 智能体根据工具调用结果输出分析报告

![image-20250918101425789](./img/image-20250918101425789.png)

![image-20250918101443421](./img/image-20250918101443421.png)

## 五、默认智能体的使用

### 5.1 hce运维助手

hce运维助手包含2个mcp服务，以下为工具列表

##### shell_generator 服务

| 工具名称           | 参数                                                         | 功能描述                                                     |
| ------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| cmd_generator_tool | 必选参数： - goal：用户的需求（自然语言描述） 可选参数： - host：远程主机名称或 IP 地址（不提供则默认本地主机） | 根据用户的自然语言需求，结合目标主机（本地或远程）的系统信息（包括系统版本、运行时间、资源使用情况等），生成适配的 Shell 命令 |
| cmd_executor_tool  | 必选参数： - command：需要执行的 Shell 命令 可选参数： - host：远程主机名称或 IP 地址（不提供则默认本地主机） | 在指定主机（本地或远程）上执行 Shell 命令，返回命令执行结果；若执行出错，返回错误信息 |

##### remote_info_mcp 服务

| 工具名称                | 参数                                                         | 功能描述                                                     |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| top_collect_tool        | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） - k：进程数量（默认 5） | 获取本地或远程主机内存占用最多的 k 个进程信息，包含进程 ID、名称、内存使用量（MB） |
| get_process_info_tool   | 必选参数： - pid：进程 ID 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机指定 PID 进程的详细信息，含状态、创建时间、CPU / 内存使用等 |
| change_name_to_pid_tool | 必选参数： - name：进程名称 可选参数： - host：远程主机名称 / IP（默认本地） | 根据进程名称获取本地或远程主机对应的 PID 列表，以空格分隔返回 |
| get_cpu_info_tool       | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机 CPU 信息，含物理 / 逻辑核心数、频率、各核心使用率 |
| memory_anlyze_tool      | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 分析本地或远程主机内存使用情况，含总内存、可用 / 已用内存、使用率 |
| get_disk_info_tool      | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机磁盘信息，含设备名称、挂载点、容量及使用率 |
| get_os_info_tool        | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机操作系统类型及版本信息，返回字符串格式     |
| get_network_info_tool   | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机网络接口信息，含接口名称、IP / 子网掩码 / MAC 地址、启用状态 |
| write_report_tool       | 必选参数： - report：报告内容字符串 可选参数：无             | 将分析结果写入本地报告文件，返回文件绝对路径                 |
| telnet_test_tool        | 必选参数： - host：远程主机名称 / IP - port：端口号（1-65535） 可选参数：无 | 测试本地到目标主机指定端口的 Telnet 连接，返回布尔值表示连接是否成功 |
| ping_test_tool          | 必选参数： - host：远程主机名称 / IP 可选参数：无            | 测试本地到目标主机的 Ping 连接，返回布尔值表示连接是否成功   |
| get_dns_info_tool       | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） | 获取本地或远程主机 DNS 配置信息，含 DNS 服务器列表、搜索域列表 |
| perf_data_tool          | 必选参数：无 可选参数： - host：远程主机名称 / IP（默认本地） - pid：进程 ID（默认所有进程） | 收集本地或远程主机性能数据，含 CPU / 内存使用率、I/O 统计信息 |

#### 使用方法参考4shell端的使用，可根据工具能力咨询相关问题或者执行命令

如果需要查询远程服务器相关能力，需要配置/usr/lib/euler-copilot-framework/mcp_center/config/public/public_config.toml

~~~json
# 公共配置文件
# 语言设置，支持zh(中文)和en(英文)
language = "zh"
# 大模型配置
llm_remote = "https://dashscope.aliyuncs.com/compatible-mode/v1"
llm_model = "qwen3-coder-480b-a35b-instruct"
llm_api_key = ""
max_tokens = 8192
temperature = 0.7
# 远程主机列表配置
[[remote_hosts]]
name = "本机"
os_type = "openEuler"
host = "116.63.xx.xx"
port = 22
username = "root"
password = "xxxxxx"
~~~



### 5.2 systrace运维助手

systrace运维助手为sysTrace的mcp化服务，提供感知、定界和报告生成三个tool

| 工具名称                  | 参数                                                         | 功能描述                                                     |
| ------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| slow_node_perception_tool | 必选参数： - task_id：任务 ID（格式如 IP 地址，例：192.168.2.122） 可选参数：无 | 检测指定 task_id 对应的机器性能是否发生劣化，返回包含异常标识及性能数据的感知结果；根据结果是否异常决定后续调用`slow_node_detection_tool`或直接调用`generate_report_tool` |
| slow_node_detection_tool  | 必选参数： - performance_data：感知工具返回的完整性能数据（PerceptionResult 类型） 可选参数：无 | 仅在`slow_node_perception_tool`返回`is_anomaly=True`时调用，对劣化节点进行慢卡定界分析，输出定界结果（含异常节点、指标等信息），需后续调用`generate_report_tool`生成报告 |
| generate_report_tool      | 必选参数： - source_data：感知结果（PerceptionResult）或定界结果（AIJobDetectResult） - report_type：报告类型（ReportType 枚举，可选 normal/anomaly） 可选参数：无 | 接收感知或定界结果，按指定类型生成 Markdown 格式的《AI 训练任务性能诊断报告》，未劣化时输出正常结论，劣化时输出异常详情及建议 |

systrace运维助手的使用需要搭配systrace的数据采集部分，参考链接为[docs/0.quickstart.md · openEuler/sysTrace - 码云 - 开源中国](https://gitee.com/openeuler/sysTrace/blob/master/docs/0.quickstart.md)

#### 5.2.1 在目标服务器上安装systrace数据采集模块，对ai训练任务进行数据采集

sysTrace是一款运用于在AI训练任务中的软件，在AI训练中，常常出现训练任务故障导致训练成本浪费，业务痛点如下：

- AI训练性能故障缺乏常态化监控、检测能力
- Host bound引发的AI任务慢，卡故障缺乏全栈跟踪能力

sysTrace工具支持如下功能：

- 采集torch_npu层的python函数的调用栈
- 采集cann层的内存持有情况，判断是否发生HBM OOM故障
- 采集mspti的通信算子下发/执行，判断是否发生算子慢的情况，从而定位到慢卡
- 采集oncpu/offcpu事件，判断AI训练中是否存在其他进程抢占cpu导致训练慢的问题

- ### 环境

- l**OS**： openEuler 22.03 (LTS-SP4) --5.10.0-60.18.0.50.oe2203.aarch64

- l**软件版本**：CANN 8.0RC3, torch 2.1.0, torch_npu 2.1.0.post10

- ## 编译

- - 下载源码：https://gitee.com/openeuler/sysTrace.git

  - 安装依赖包

    ```
    ## 软件包版本：libbpf >= 0.8.1, clang >= 10.0.0 gcc >= 8.3.0, bpftool >= 6.8.0，如果版本均满足则跳过下面的手动安装步骤
    [root@localhost sysTrace] yum install gcc g++ cmake make python3-devel protobuf-compiler protobuf-devel protobuf-c-devel libbpf clang libbpf-devel bpftool
    ```

  - 手动安装libbpf

    ```
    [root@localhost ~] git clone https://github.com/libbpf/libbpf.git
    [root@localhost ~] git checkout v0.8.1
    [root@localhost ~] cd libbpf/src
    [root@localhost ~] make && make install
    ```

  - 手动安装bpftool

    ```
    [root@localhost ~] git clone --recurse-submodules https://github.com/libbpf/bpftool.git
    [root@localhost ~] git submodule update --init
    [root@localhost ~] cd src
    [root@localhost ~] make
    [root@localhost ~] make install
    ```

  - 编译

    ```
    [root@localhost sysTrace] cd sysTrace
    [root@localhost sysTrace] bash build.sh
    ## 编译产物均在build目录下，会用到libsysTrace.so和sysTrace_cli
    [root@localhost build]# ll
    total 1776
    -rw-r--r--. 1 root root   17000 Jun 12 16:58 CMakeCache.txt
    drwxr-xr-x. 7 root root    4096 Jun 12 17:10 CMakeFiles
    -rw-r--r--. 1 root root    1798 Jun 12 16:58 cmake_install.cmake
    -rw-r--r--. 1 root root  534270 Jun 12 17:10 libcommon.a
    -rwxr-xr-x. 1 root root 1209296 Jun 12 17:10 libsysTrace.so
    -rw-r--r--. 1 root root   20479 Jun 12 17:10 Makefile
    drwxr-xr-x. 3 root root    4096 Jun 12 17:10 protos
    -rwxr-xr-x. 1 root root   76736 Jun 12 17:10 sysTrace_cli
    ```

- ## 使用

- ### 数据采集

- 修改AI训练任务脚本，使用LD_PRELAOD的方式将动态库加载到AI训练任务中

- ```
  LD_PRELOAD=/usr/local/lib/libunwind.so.8.2.0:/usr/local/lib/libunwind-aarch64.so.8.2.0:/home/ascend-toolkit-bak/ascend-toolkit/8.0.RC3.10/tools/mspti/lib64/libmspti.so:<path-to-sysTrace>/systrace/build/libsysTrace.so python ...
  ```

- **注意：以LD_PRELOAD的方式加载了/usr/local/lib/libunwind.so.8.2.0:/usr/local/lib/libunwind-aarch64.so.8.2.0的原因是因为低于1.7版本的libunwind有bug，需要手动下载最新版本的libunwind，如果环境中的libunwind版本大于等于1.7，则使用以下命令**

- ```
  LD_PRELOAD=/home/ascend-toolkit-bak/ascend-toolkit/8.0.RC3.10/tools/mspti/lib64/libmspti.so:<path-to-sysTrace>/systrace/build/libsysTrace.so python ...
  ```

- ### 动态开关

- sysTrace支持动态开启采集数据，采集数据类型支持动态开启，sysTrace提供二进制工具sysTrace_cli，当前L0数据是常态开启，L1/2/3类型数据可自行决定是否开启，使用命令如下：

- ```
  [root@localhost ~]# sysTrace_cli help
  Usage: sysTrace_client <command> [args]
  Commands:
    set <level>=<true|false> - Enable/disable dump level
                              (levels: L0, L1, L2, L3)
    interval <level>=<value> - Set dump interval in minutes
                              (levels: L1, L2, L3)
    print [level|all]        - Print current settings
                              (levels: L0, L1, L2, L3, all)
  
  Examples:
    sysTrace_cli set L1=true
    sysTrace_cli interval L1=10
    sysTrace_cli print all
  ```

- ### 数据落盘

- 所有采集的数据当前存放在`/home/sysTrace`目录下，每张卡上的数据以独立一个文件保存，集群多节点环境，建议将保存目录`/home/sysTrace`映射到共享目录，否则需要手动将每台节点上的数据手动拷贝，如下：

- ```
  [root@localhost sysTrace]# ll
  drwxr-xr-x. 2 root root 4096 Jun 12 17:01 cann ##内存数据
  drwxr-xr-x. 2 root root 4096 Jun 12 17:01 mspti ##通信算子数据
  drwxr-xr-x. 2 root root 4096 Jun 12 17:01 timeline ##torch_npu层数据
  drwxr-xr-x. 2 root root 4096 Jun 12 17:01 osprobe ##offcpu/cpu事件
  ```

- sysTrace支持动态开启采集数据，当前支持以下级别的数据：

- - L0：采集torch_npu层数据，采集数据类型包括如下数据(常态化采集)

    ```
    message Pytorch {
      repeated PytorchStage pytorch_stages = 1;
      uint32 rank = 2; // rank号
    }
    
    message PytorchStage {
      uint32 stage_id = 1; // AI训练迭代轮次
      string stage_type = 2; // AI训练迭代阶段
      uint64 start_us = 3; // 当前迭代阶段的开始时间
      uint64 end_us = 4; // 当前迭代阶段的结束时间
      repeated string stack_frames = 5; //当前迭代阶段的python调用栈
      oneof debug_data {
        GcDebugData gc_debug = 6; //当前迭代阶段的GC数据
      }
    }
    ```

  - L1：采集通信算子数据，采集数据包括如下数据

    ```
    Flag,Id,Kind,Name,SourceKind,Timestamp,msptiObjectId_Ds_DeviceId,msptiObjectId_Ds_StreamId,msptiObjectId_Pt_ProcessId,msptiObjectId_Pt_ThreadId
    ```

#### 5.2.2 修改systrace运维助手的配置文件配合数据采集模块对ai训练任务结果进行分析

​	在/etc/systrace/config目录下修改ftp_config.json文件

~~~json
{
  "servers": [
    {
      "ip": "192.168.xxx.196",  #远程目标服务器的ip
      "port": 22, #远程目标服务器的ssh端口
      "user": "root", #用户名
      "password": "password", #密码
      "perception_remote_dir": "/home/sysTrace/timeline", #远程目标服务器systrace采集的timeline数据保存路径
      "detection_remote_dir": "/home/sysTrace/mspti",#远程目标服务器systrace采集的mspti数据保存路径
    }
  ],
  "enable": "True" #True 为开启远程获取数据，False为关闭只使用本地文件进行分析
}

~~~

修改model_config.json文件，主要是数据保存的路径，其他参数参考[docs/0.quickstart.md · openEuler/sysTrace - 码云 - 开源中国](https://gitee.com/openeuler/sysTrace/blob/master/docs/0.quickstart.md)

~~~json
"training_log":"/home/sysTrace/timeline" # 感知数据的保存路径
"root_path": "/home/sysTrace/mspti", # 定界数据的保存路径
~~~

~~~json
慢卡定界算法配置
在文件model_config.json中，配置模型运行所需的参数。该配置项中，主要包含：

with_fail_slow: 配置启动慢节点检测性能劣化来源于性能劣化检测的时刻还是手动配置, 默认为false

slow_node_detection_range_times：慢节点检测输入的时间范围，默认为空列表

slow_node_detection_time_span_hours：慢节点检测的时间长度，默认为0.5小时

slow_node_detection_path：慢节点检测结果保存路径，默认为"/etc/systrace/result/slow_node"

data_type：算子数据的格式，默认为”json“

root_path: 算子数据的输入路径，默认为”/home/hbdir/systrace_failslow/data/baseline“

enable_detect_type：检测不同故障类型的开关，字典格式

enable_cal: 计算慢开关，默认为true

enable_op_launch: 算子下发慢开关，默认为false

enable_op_launch: Kafka对应的server port，如："9092"；

enable_comm: 通信慢开关，默认为false

enable_dataloader: 输入模型数据加载慢开关，默认为false

enable_ckpt: 模型保存慢开关，默认为false

fail_slow_ops: 检测不同故障类型对应的观测点，字典格式

cal_slow：计算慢对应的观测点，默认为"HcclAllGather"
op_launch_slow：算子下发慢对应的观测点，默认为“HcclAllGather_launch”
comm_slow：通信慢对应的观测点，默认为“HcclBatchSendRecv”
dataloader_slow：输入模型数据加载慢对应的观测点，默认为“Dataloader”
ckpt_slow: 模型保存满对应的观测点，默认为“SaveCkpt”
save_image：时序数据保存的路径，用于debug算法效果，默认为“image”

record_kpi: 时序数据是否记录到检测结果中，默认为false
use_plot: 时序数据保存开关，用于debug算法效果，默认为false
max_num_normal_results：检测结果最大记录正常节点数据数量，默认为16
look_back：告警抑制，默认为20min
hccl_domain: 通信域默认配置，格式为字典，默认为{}，实际配置示例{"tp":[[0,1,2,3], [4,5,6,7]], "dp":[[0,4], [1,5],[2,6],[3,7]]}
rank_table_json: rank_table配置文件路径，用于mindspore通信域配置，默认路径"./rank_table.json"
debug_data：denug模式，会保存算子执行和算子下发的中间文件，默认为false
在文件metric_config.json中，配置所有指标的检测算法参数，每个指标独立配置。该配置项中以HcclAllGather指标配置举例，主要包含：

metric_type：指标类型，string类型，取值“device”和“host”，

aggregation：指标聚合配置，字典

during_s：聚合窗口大小, int类型，默认5s
funcs：聚合方法配置，list类型，包含元素为dict类型
func: 聚合方法，string类型，有“min”,"max","mean","percentile"等
func_params: 聚合方法配置参数，字典类型，根据不同的聚合方法配置，默认为空
priority：指标类型，string类型，取值“device”和“host”，

aggregation：检测优先级，int类型

alarm_filter_window_size：告警过滤窗口大小，表示检测出的异常点连续个数，int类型，默认值为5

space_detector: 节点间对比检测器配置，不配置为“null”

dist_metric: 节点间距离函数类型，“euclidean”, string类型
eps：Dbscan聚类参数的阈值，点间距离大于该值则为另一类， float类型
cv_threshold：判断值偏离均值的程度，偏移过大则认为是异常点，float类型
min_samples：dbscan最小成新簇的点数, int类型
window_size：窗口大小，表示单次检测的窗口，不重叠，int类型
scaling：表示时间序列是否归一化， bool类型
type：空间检测器类型，string类型，取值“SlidingWindowDBSCAN”，“OuterDataDetector”
time_detector:单节点时序异常检测配置, 不配置为“null”

preprocess_eps: Dbscann预处理的阈值, float类型
preprocess_min_samples：Dbscan预处理的最小点数，int类型
type：时间检测器类型，string类型，取值为“TSDBSCANDetector”，“SlidingWindowKSigmaDetector”
n_sigma_method：当为“SlidingWindowKSigmaDetector”类型时，配置字段，dict类型
type：SlidingWindowKSigmaDetector采用的检测算法，可替换扩展，string类型，默认为”SlidingWindowNSigma“
training_window_size：滑动窗口的最大值，超过该值，覆盖已有value，int类型
min_update_window_size：滑动窗口的最小更新值，int类型
min_std_val：最小标准差，当标准差为0时，设置为最小标准差，float类型
bias：边界基础上的偏置系数，float类型
abs_bias：边界基础上的偏置值，float类型
nsigma_coefficient：Ksigam的系数，int类型
detect_type：检测边界类型，string类型，取值为“lower_bound”,“upper_bound”,“bi_bound”
min_expert_lower_bound：下边界最小专家阈值，null表示不设置专家阈值，int或者null类型
max_expert_lower_bound：下边界最大专家阈值，null表示不设置专家阈值，int或者null类型
min_expert_upper_bound：上边界最小专家阈值，null表示不设置专家阈值，int或者null类型
max_expert_upper_bound：上边界最大专家阈值，null表示不设置专家阈值，int或者null类型
~~~



#### 5.2.3 shell客户端使用systrace运维助手对训练采集数据进行分析

问题需要带上目标ip

如：帮我分析192.168.122.196机器的ai训练情况

### 5.3 euler-copilot-tune调优助手

EulerCopilot Tune通过采集系统、微架构、应用等维度的指标数据，结合大模型和定制化的prompt工程，针对不同应用的可调参数给出可靠的参数推荐，同时根据推荐的参数运行benchmark，与baseline做对比并计算出推荐参数对应用性能的提升值。

仓库地址：[README.md · openEuler/A-Tune - 码云 - 开源中国](https://gitee.com/openeuler/A-Tune/blob/euler-copilot-tune/README.md)

| 工具名称  | 参数   | 功能描述                                                     |
| --------- | ------ | ------------------------------------------------------------ |
| Collector | 无参数 | 采集指定机器的性能指标，包括静态指标（系统配置等）、动态指标（实时性能数据）和可选的微依赖分析数据，并将结果缓存 |
| Analyzer  | 无参数 | 对已采集的数据进行分析，识别性能瓶颈，生成分析报告（需先调用 Collector） |
| Optimizer | 无参数 | 基于分析结果提供参数优化建议和策略优化方案（需先调用 Analyzer） |
| StartTune | 无参数 | 执行实际调优操作，包括参数优化和策略优化，耗时小时级，结果需通过日志查看（需先完成 Collector、Analyzer、Optimizer 流程，且仅在用户明确要求时调用），指令：journalctl -xe -u tune-mcpserver --all -f |

#### 工具调用流程说明

1. **数据采集阶段**：先调用`Collector`工具，获取机器的静态配置和动态性能指标，数据将自动缓存。
2. **分析阶段**：调用`Analyzer`工具，基于采集的数据生成性能分析报告并识别瓶颈。
3. **优化建议阶段**：调用`Optimizer`工具，根据分析结果提供参数调整和策略优化方案。
4. **执行调优阶段**：仅当用户明确要求时，调用`StartTune`工具执行实际调优，完成后需通过日志（`journalctl -xe -u tune-mcpserver --all -f`）查看结果。

#### 注意事项

- 工具需按顺序调用，前序工具未执行会导致后续工具报错。
- `StartTune`工具执行耗时较长（约 1 小时），调用时需提醒用户耐心等待。

#### 5.3.1 使用前需修改配置文件指定要调优的机器和调优的系统

在/etc/euler-copilot-tune/config目录下修改.env.yaml文件

具体格式如下：

```
LLM_KEY: "YOUR_LLM_KEY"
LLM_URL: "YOUR_LLM_URL"
LLM_MODEL_NAME: "YOUR_LLM_MODEL_NAME"
LLM_MAX_TOKENS:

REMOTE_EMBEDDING_ENDPOINT: "YOUR_EMBEDDING_MODEL_URL"
REMOTE_EMBEDDING_MODEL_NAME: "YOUR_MODEL_NAME"

servers:
  - ip: ""                                                              #应用所在ip
    host_user: ""                                                       #登录机器的usr id
    password: ""                                                        #登录机器的密码
    port:                                                               #应用所在ip的具体port
    app: "mysql"                                                        #当前支持mysql、nginx、pgsql、spark
    listening_address: ""                                               #应用监听的ip(当前仅flink、nginx、spark需要填写)
    listening_port: ""                                                  #应用监听的端口(当前仅flink、nginx、spark需要填写)
    target_process_name: "mysqld"                                       #调优应用的name
    business_context: "高并发数据库服务，CPU负载主要集中在用户态处理"           #调优应用的描述（用于策略生成）
    max_retries: 3
    delay: 1.0
    
feature:
  - need_restart_application: False                                     #修改参数之后是否需要重启应用使参数生效
    need_recover_cluster: False                                         #调优过程中是否需要恢复集群
    microDep_collector: True                                            #是否开启微架构指标采集
    pressure_test_mode: True                                            #是否通过压测模拟负载环境
    tune_system_param: False                                            #是否调整系统参数
    tune_app_param: True                                                #是否调整应用参数
    strategy_optimization: False                                        #是否需要策略推荐
    benchmark_timeout: 3600                                             #benchmark执行超时限制
    max_iterations: 10                                                  #最大迭代轮数
```

在/etc/euler-copilot-tune/config目录下修改app_config.yaml中（重点是补充set_param_template、get_param_template、benchmark脚本），具体内容如下：

```
mysql:
  user: "root"
  password: "123456"
  config_file: "/etc/my.cnf"
  port: 3306
  set_param_template: 'grep -q "^$param_name\\s*=" "$config_file" && sed -i "s/^$param_name\\s*=.*/$param_name = $param_value/" "$config_file" || sed -i "/\\[mysqld\\]/a $param_name = $param_value" "$config_file"'
  get_param_template: 'grep -E "^$param_name\s*=" $config_file | cut -d= -f2- | xargs'
  stop_workload: "systemctl stop mysqld"
  start_workload: "systemctl start mysqld"
  benchmark: "$EXECUTE_MODE:local sh $SCRIPTS_DIR/mysql/parse_benchmark.sh $host_ip $port $user $password"
  performance_metric: "QPS"

flink:
  set_param_template: 'sh /home/wsy/set_param.sh $param_name $param_value'
  get_param_template: 'sh /home/wsy/get_param.sh $param_name'
  benchmark: "sh /home/wsy/nexmark_test.sh"
  stop_workload: 'docker exec -i flink_jm_8c32g bash -c "source /etc/profile && /usr/local/flink-1.16.3/bin/stop-cluster.sh && /usr/local/nexmark/bin/shutdown_cluster.sh"'
  start_workload: 'docker exec -i flink_jm_8c32g bash -c "source /etc/profile && /usr/local/flink-1.16.3/bin/start-cluster.sh"'
  performance_metric: "THROUGHPUT"

pgsql:
  user: "postgres"
  password: "postgres"
  config_file: "/data/data1/pgsql/postgresql.conf"
  port: 5432
  set_param_template: 'grep -qE "^\s*$param_name\s*=" "$config_file" && sed -i "s/^[[:space:]]*$param_name[[:space:]]*=.*/$param_name = $param_value/" "$config_file" || echo "$param_name = $param_value" >> "$config_file"'
  get_param_template: 'grep -oP "^\s*$param_name\s*=\s*\K.*" "$config_file"'
  stop_workload: "su - postgres -c '/usr/local/pgsql/bin/pg_ctl stop -D /data/data1/pgsql/ -m fast'"
  start_workload: "su - postgres -c '/usr/local/pgsql/bin/pg_ctl start -D /data/data1/pgsql/ -l /var/log/postgresql/postgresql.log'"
  benchmark: "$EXECUTE_MODE:local sh $SCRIPTS_DIR/postgresql/parse_benchmark.sh $host_ip $port $user $password"
  performance_metric: "QPS"

spark:
  set_param_template: 'sh /path/of/set_param.sh $param_name $param_value'
  get_param_template: 'sh /path/of/get_param.sh $param_name'
  benchmark: "sh /path/of/spark_benchmark.sh"
  performance_metric: "DURATION"

nginx:
  port: 10000
  config_file: "/usr/local/nginx/conf/nginx.conf"
  set_param_template: 'grep -q "^\\s*$param_name\\s\\+" "$config_file" && sed -i "s|^\\s*$param_name\\s\\+.*|    $param_name $param_value;|" "$config_file" || sed -i "/http\\s*{/a\    $param_name $param_value;" "$config_file"'
  get_param_template: 'grep -E "^\\s*$param_name\\s+" $config_file | head -1 | sed -E "s/^\\s*$param_name\\s+(.*);/\\1/"'
  stop_workload: "/usr/local/nginx/sbin/nginx -s reload"
  start_workload: "/usr/local/nginx/sbin/nginx -s reload"
  benchmark: "$EXECUTE_MODE:local sh $SCRIPTS_DIR/nginx/parse_benchmark.sh $host_ip $port"
  performance_metric: "QPS"

ceph:
  set_param_template: 'ceph config set osd "$param_name" "$param_value"'
  get_param_template: 'sh /path/of/get_params.sh'
  start_workload: "sh /path/of/restart_ceph.sh"
  benchmark: "$EXECUTE_MODE:local sh $SCRIPTS_DIR/ceph/parse_benchmark.sh"
  performance_metric: "BANDWIDTH"

gaussdb:
  user: ""
  password: ""
  config_file: "/path/of/config_file"
  port: 5432
  set_param_template: 'gs_guc set -Z datanode  -N all -I all -c "${param_name}=${param_value}"'
  get_param_template: 'gs_guc check -Z datanode -N all -I all -c "${param_name}"'
  stop_workload: "cm_ctl stop -m i"
  start_workload: "cm_ctl start"
  recover_workload: "$EXECUTE_MODE:local sh /path/of/gaussdb_cluster_recover.sh"
  benchmark: "$EXECUTE_MODE:local sh/path/of/gaussdb_benchmark.sh"
  performance_metric: "DURATION"

system:
  set_param_template: 'sysctl -w $param_name=$param_value'
  get_param_template: 'sysctl $param_name'

redis:
  port: 6379
  config_file: "/etc/redis.conf"
  set_param_template: "sed -i 's/^$param_name/$param_name $param_value/g' $config_file"
  get_param_template: "grep -P '$param_name' $config_file | awk '{print $2}"
  start_workload: "systemctl start redis"
  stop_workload: "systemctl stop redis"
  benchmark: "$EXECUTE_MODE:local sh $SCRIPTS_DIR/redis/parse_benchmark.sh $host_ip $port "
  performance_metric: "QPS"
```

其中： set_param_template:根据调优结果修改应用参数，用于后续测试效果 get_param_template:获取应用参数 recover_workload: 恢复集群 benchmark:benchmark脚本，脚本可参考/etc/euler-copilot-tune/scripts 结合业务需求自定义

5.3.2 根据调优工具进行使用，采集数据，分析，推荐参数以及开始调优
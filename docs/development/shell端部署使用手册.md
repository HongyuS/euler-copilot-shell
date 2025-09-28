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

使用智能体的基本步骤如[shell客户端使用](#四shell客户端的使用)中所示：

①打开shell客户端；
~~~bash
oi
~~~

②选择智能体；

③进行对话即可；

④若需要获取进行远程服务器操作的能力，需提前配置/usr/lib/euler-copilot-framework/mcp_center/config/public/public_config.toml中的**远程主机列表配置**，配置完成即可对列表中的主机进行相关的操作。

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

### 5.1 OE-通用运维助手

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

- #### 环境

- l**OS**： openEuler 22.03 (LTS-SP4) --5.10.0-60.18.0.50.oe2203.aarch64

- l**软件版本**：CANN 8.0RC3, torch 2.1.0, torch_npu 2.1.0.post10

- #### 编译

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

- #### 使用

- #### 数据采集

- 修改AI训练任务脚本，使用LD_PRELAOD的方式将动态库加载到AI训练任务中

- ```
  LD_PRELOAD=/usr/local/lib/libunwind.so.8.2.0:/usr/local/lib/libunwind-aarch64.so.8.2.0:/home/ascend-toolkit-bak/ascend-toolkit/8.0.RC3.10/tools/mspti/lib64/libmspti.so:<path-to-sysTrace>/systrace/build/libsysTrace.so python ...
  ```

- **注意：以LD_PRELOAD的方式加载了/usr/local/lib/libunwind.so.8.2.0:/usr/local/lib/libunwind-aarch64.so.8.2.0的原因是因为低于1.7版本的libunwind有bug，需要手动下载最新版本的libunwind，如果环境中的libunwind版本大于等于1.7，则使用以下命令**

- ```
  LD_PRELOAD=/home/ascend-toolkit-bak/ascend-toolkit/8.0.RC3.10/tools/mspti/lib64/libmspti.so:<path-to-sysTrace>/systrace/build/libsysTrace.so python ...
  ```

- #### 动态开关

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

- #### 数据落盘

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

- #### 5.2.2 修改systrace运维助手的配置文件配合数据采集模块对ai训练任务结果进行分析

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



- #### 5.2.3 shell客户端使用systrace运维助手对训练采集数据进行分析

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

#### 5.3.2 根据调优工具进行使用，采集数据，分析，推荐参数以及开始调优




### 5.4 OE-core 运维助手
OE-Core 是Euler-Copilot-Framework智能体群的核心全能型助手，定位为 “系统基础运维一站式工具集”。其整合系统监控、文件管理、进程管控三大类 MCP 服务，无需切换多工具即可完成日常运维中 80% 的基础操作，覆盖从 “系统状态查看” 到 “文件操作” 再到 “进程管理” 的全流程需求。

其核心价值在于打破传统运维中“系统监控用 top/free、文件操作靠 rm/tar、进程管理需 ps/kill”的工具碎片化现状，通过标准化 MCP 工具封装与结构化数据输出，实现“一站式操作+自动化适配”——既支持本地主机快速巡检，也可通过 SSH 认证对接远程集群，适配 x86_64、arm64 多架构服务器，兼容 EulerOS、CentOS、Ubuntu 等主流 Linux 发行版，满足中小规模集群及单机运维的基础需求。
#### 5.4.1 MCP服务矩阵
智能体通过 14 个标准化 MCP 工具，构建“全场景覆盖、轻量化操作”的服务体系，涵盖系统监控、文件管理、进程管控三大运维维度，具体服务与工具映射如下：
| 服务分类         | MCP 工具名称                | 核心功能定位               | 默认端口  |
|------------------|-----------------------------|----------------------------|-----------|
| 系统综合状态洞察 | [top_mcp](#top_mcp)         | 实时监控系统负载与进程状态，支持自定义采集维度 | 12110     |
|                  | [free_mcp](#free_mcp)       | 查看系统内存使用状态       | 13100     |
|                  | [vmstat_mcp](#vmstat_mcp)   | 采集系统资源交互瓶颈数据   | 13101     |
|                  | [nvidia_mcp](#nvidia_mcp)   | 查询 GPU 负载与状态        | 12114     |
| 文件与目录管理   | [ls_mcp](#ls_mcp)           | 查看目录内容与文件属性     | 13112     |
|                  | [file_content_tool_mcp](#file_content_tool_mcp) | 文件内容增删改查         | 12125     |
|                  | [find_mcp](#find_mcp)       | 按条件搜索文件/目录       | 13107     |
|                  | [grep_mcp](#grep_mcp)       | 搜索文件内容关键词         | 13120     |
|                  | [rm_mcp](#rm_mcp)           | 删除文件/目录             | 13110     |
|                  | [mv_mcp](#mv_mcp)           | 文件/目录移动或重命名      | 13111     |
|                  | [mkdir_mcp](#mkdir_mcp)     | 创建目录（支持多级）       | 13109     |
|                  | [tar_mcp](#tar_mcp)         | 文件/目录压缩解压（tar格式）| 13118     |
|                  | [zip_mcp](#zip_mcp)         | 文件/目录压缩解压（zip格式）| 13119     |
| 进程基础管理     | [kill_mcp](#kill_mcp)       | 暂停/恢复进程，查看信号量  | 12111     |

#### 5.4.2 使用案例
以下按 “系统监控、文件管理、进程管控、综合运维” 四大高频场景分类，提供不同需求粒度的 Prompt 格式，直接复制即可使用，无需额外补充技术参数,只需替换ip或者一些目标信息即可

**系统监控类场景（核心需求：查状态、判异常）**
~~~
#案例1：远程单点服务器基础状态巡检（最常用场景）

帮我查一下 192.168.3.5 这台服务器的运行状态，要包含 CPU 负载（1/5/15分钟）、内存实际使用率（排除缓存）、GPU 显存和核心占用率，最后告诉我有没有异常

#方案 2：本地节点资源告警排查

我本地机器提示“内存不足”，帮我确认一下总内存、已用内存、缓存占用多少，再看看哪些进程内存占比最高，Top3 就行

#方案 3：多节点负载对比

帮我批量查一下 192.168.3.5、192.168.3.6、192.168.3.7 这三台服务器的 CPU 空闲率和磁盘根目录使用率，整理成对比结果

#方案 4：GPU 专项检查

192.168.3.10 这台 GPU 服务器的训练任务卡住了，帮我看看有几块 GPU、每块的显存使用率是不是超 90%，还有哪些进程在占用 GPU 资源

~~~
**文件管理类场景（核心需求：找文件、改内容、做归档）**
~~~
#方案 1：远程过期日志清理

192.168.3.5 的 /var/log/nginx 目录下，帮我找所有 30 天前的 .log 文件，先压缩成 tar.gz 包存到 /var/log/archive，再把原文件删掉

方案2：本地多文件内容修改

我本地 /data/app 目录下，所有子目录里的 config.yaml 文件，帮我把“timeout: 30s”改成“timeout: 60s”，改完后确认一下修改结果

方案 3：按条件查找大文件

帮我在 192.168.3.6 的 /data 目录下，找所有大于 10GB 的 .tar 或 .zip 压缩文件，显示文件路径、大小和最后修改时间

方案 4：文件内容关键词搜索

192.168.3.5 的 /var/log/messages 文件里，帮我搜索最近 7 天包含“error”或“fail”的日志，输出匹配的行号和内容
~~~

**进程管控类场景（核心需求：查进程、解阻塞）**

~~~
#方案 1：本地高负载进程临时暂停

我本地有个叫“data_export”的进程，现在 CPU 占比快 90% 了，先帮我查它的 PID，然后暂停这个进程，暂停后再确认一下它的状态是不是“stopped”

#方案 2：远程关键进程恢复运行

192.168.3.5 上有个叫“redis-server”的进程之前暂停了（PID 1234），帮我恢复它的运行，恢复后验证进程状态是否正常，还要看它的内存占比有没有异常

#方案 3：批量暂停同类临时进程

我本地运行了多个叫“test_task”的临时进程，帮我先列出所有这类进程的 PID 和状态，然后把它们全部暂停，最后输出暂停成功的 PID 列表

#方案 4：按 PID 精准暂停与恢复（应急场景）

帮我先查看 PID 5678 的进程名称和当前状态，确认是“app_worker”后暂停它；等 10 秒后，再恢复这个 PID 5678 进程的运行，全程记录状态变化

#方案 5：常用信号量含义查询（基础认知）

我想了解一下进程管理里常用的几个信号量含义，帮我解释下 SIGSTOP（19）、SIGCONT（18）、SIGTERM（15）这三个信号分别是做什么的，适合在什么场景用

#方案 6：应急信号量查询（操作前确认）

现在要恢复一个之前被暂停的“file_sync”进程，不确定该用哪个信号量，帮我查一下“恢复暂停进程”对应的信号量名称、编号和使用注意事项
~~~

**综合运维类场景（多需求组合）**
~~~
#方案 1：服务器初始化检查

新部署的 192.168.3.20 服务器，帮我做个初始化检查：1. 查 CPU 核心数、内存总大小；2. 看 /data 目录是否存在，不存在就创建；3. 确认 sshd 进程是否在运行

#方案 2：应用部署前环境确认

要在 192.168.3.8 部署 Java 应用，帮我确认：1. 内存空闲是否超 16GB；2. /opt/app 目录是否有写权限；3. 有没有占用 8080 端口的进程

#方案 3：故障应急排查

192.168.3.9 的 nginx 服务没响应，帮我排查：1. nginx 进程是否存活；2. CPU 和内存有没有满；3. /var/log/nginx/error.log 里最近 10 条错误日志是什么
~~~


### 5.5 OE-PerfDoctor 性能诊断医师
OE-PerfDoctor 是 Euler-Copilot-Framework体系下的**系统级性能智能诊断智能体**，专注于服务器集群、关键业务应用的性能瓶颈定位与优化建议生成。其核心能力在于整合底层硬件分析、内存访问监控、CPU 性能剖析及高级诊断工具链，通过“自动化工具调用+多维度数据联动分析+可视化结果呈现”的流程，替代传统人工性能调优中的重复性操作，大幅提升性能问题排查效率。

OE-PerfDoctor 已集成四大类核心性能分析服务，覆盖从硬件基线到应用层瓶颈的全链路诊断，支持 x86_64、arm64 多架构服务器，适配 EulerOS、CentOS、Ubuntu 等主流 Linux 发行版。



#### 5.5.1 MCP服务矩阵
OE-PerfDoctor是 Euler-Copilot-Framework 中的性能深度诊断专家，专注于系统级性能问题的定位和优化。该智能体通过 10 个标准化 MCP 工具，构建 “硬件 - 系统 - 应用” 全链路的性能诊断体系，涵盖 NUMA 架构分析、CPU 性能剖析、系统调用与中断诊断三大维度，具体服务与工具映射如下：
| 服务分类               | MCP 工具名称                | 核心功能定位                                   | 默认端口  |
|------------------------|-----------------------------|------------------------------------------------|-----------|
| NUMA 架构分析与优化    | [lscpu_mcp](#lscpu_mcp)      | 采集 CPU 静态架构信息，为 NUMA 分析提供硬件基线 | 12202     |
|                        | [numa_topo_mcp](#numa_topo_mcp)  | 解析 NUMA 节点分布、CPU 与内存绑定关系          | 12203     |
|                        | [numastat_mcp](#numastat_mcp)   | 监控 NUMA 节点内存访问状态，识别分配不均衡问题  | 12210     |
|                        | [numa_cross_node_mcp](#numa_cross_node_mcp)    | 定位跨 NUMA 节点访问的进程，量化性能损耗        | 12211     |
| CPU 性能剖析           | [hotspot_trace_mcp](#hotspot_trace_mcp)      | 跟踪 CPU 热点进程/函数，识别高负载代码段        | 12216     |
|                        | [cache_miss_audit_mcp](#cache_miss_audit_mcp)   | 审计 CPU 缓存（L1/L2/L3）未命中率，定位缓存损耗 | 12217     |
|                        | [flame_graph_mcp](#flame_graph_mcp)        | 生成 CPU 耗时火焰图，可视化函数调用栈性能瓶颈   | 12222     |
|                        | [func_timing_trace_mcp](#func_timing_trace_mcp)  | 分析函数级执行耗时，定位慢函数                 | 12218     |
| 系统调用与中断诊断     | [strace_syscall_mcp](#strace_syscall_mcp)     | 统计进程系统调用频率与耗时，定位 I/O 瓶颈       | 12219     |
|                        | [perf_interrupt_mcp](#perf_interrupt_mcp)     | 定位高频中断源，识别中断导致的 CPU 资源争抢     | 12220     |
#### 5.5.2 使用案例
以下按 “NUMA 内存问题诊断、CPU 热点定位、系统调用瓶颈排查” 三大高频性能场景分类，提供自然语言交互 Prompt 格式，直接替换 IP、进程名等关键信息即可使用，无需额外补充技术参数。
~~~
#场景 1：NUMA 内存分配不均衡诊断（数据库性能下降）

192.168.4.10 这台数据库服务器查询延迟突增，帮我分析是不是 NUMA 内存问题：1. 查一下 NUMA 节点分布和各节点内存使用率；2. 看看有没有进程跨节点访问内存，占比多少；3. 最后给优化建议

#场景 2：CPU 高负载根因定位（应用响应慢）

我本地运行的“order-service”应用 CPU 一直占 85% 以上，帮我定位瓶颈：1. 找出 CPU 热点函数；2. 查一下 L3 缓存未命中率是不是超标；3. 生成火焰图看看函数调用栈哪里耗时最多

#场景 3：系统调用瓶颈排查（I/O 密集型应用卡顿）

192.168.4.15 的“file-transfer”应用传输文件时卡顿，帮我查：1. 这个进程的系统调用里，哪些调用频率高、耗时久；2. 有没有高频中断占用 CPU；3. 总结卡顿的核心原因

#场景 4：综合性能诊断（集群节点性能差异）

帮我对比 192.168.4.20 和 192.168.4.21 两台节点的性能差异：1. 查 CPU 架构和 NUMA 拓扑是否一致；2. 对比相同“data-process”进程的 CPU 热点和缓存命中率；3. 指出导致性能差异的关键因素
~~~
### 5.6 OE-高级运维工程师
 OE-AdvOps 是 mcp_center 智能体群中的专精型高级运维工具，定位为 “复杂运维场景解决方案提供者”。其聚焦企业级服务器的进阶运维需求，整合进程高级控制、系统资源深度监控、内存与交换空间管理三大核心能力，通过标准化 MCP 工具封装，替代传统 “命令拼接 + 人工判断” 的低效运维模式，实现复杂操作的自动化与可追溯，适配中大规模集群的高级运维场景。

其核心价值在于解决传统运维中 “进程后台启动靠 nohup 手动记录、资源瓶颈诊断需 sar/vmstat 多工具拼接、swap 管理风险高” 的痛点，支持本地与远程（SSH 认证）双模式操作，适配 x86_64、arm64 多架构服务器，兼容 EulerOS、CentOS、Ubuntu 等主流 Linux 发行版，可满足 “进程精细化管控、系统资源深度诊断、内存交换空间安全管理” 的高阶需求。

#### 5.6.1 MCP服务矩阵
OE-AdvOps 智能体通过 9 个标准化 MCP 工具，构建 “进程 - 资源 - 内存” 全维度的高级运维体系，涵盖进程高级控制、系统资源监控与诊断、内存与交换空间管理三大维度，具体服务与工具映射如下：
| 服务分类               | MCP 工具名称                | 核心功能定位                                   | 默认端口  |
|------------------------|-----------------------------|------------------------------------------------|-----------|
| 进程高级控制           | [nohup_mcp](#nohup_mcp)      | 后台启动进程并记录输出日志，避免会话断开中断    | 12301     |
|                        | [strace_mcp](#strace_mcp)     | 跟踪进程系统调用与信号，分析进程异常原因        | 12302     |
|                        | [kill_mcp](#kill_mcp)         | 精细化控制进程（暂停/恢复/发送指定信号），查看进程状态 | 12111     |
|                        | [top_mcp](#top_mcp)          | 实时监控进程资源占用（CPU/内存），识别高负载进程 | 12110     |
| 系统资源监控与诊断     | [sar_mcp](#sar_mcp)          | 采集系统历史/实时资源数据（CPU/内存/I/O），生成诊断报告 | 12303     |
|                        | [vmstat_mcp](#vmstat_mcp)     | 监控系统内存交换、I/O 等待、CPU 上下文切换，定位资源瓶颈 | 13101     |
| 内存与交换空间管理     | [sync_mcp](#sync_mcp)         | 同步系统缓冲区数据到磁盘，避免数据丢失          | 12304     |
|                        | [swapon_mcp](#swapon_mcp)     | 启用 swap 分区/文件，查看当前 swap 使用状态     | 13104     |
|                        | [swapoff_mcp](#swapoff_mcp)   | 安全停用 swap 分区/文件，释放交换空间          | 13105     |
|                        | [fallocate_mcp](#fallocate_mcp) | 预分配文件空间（常用于创建 swap 文件），指定大小与路径 | 12305     |
#### 5.6.2 使用案例
以下按 “进程高级管控、系统资源深度诊断、内存与交换空间管理” 三大高频高级运维场景分类，提供自然语言交互 Prompt 格式，直接替换 IP、进程名、路径等关键信息即可使用：
~~~
#场景 1：进程后台启动与异常跟踪

帮我在 192.168.5.10 上后台启动“data_sync.sh”脚本，日志输出到 /var/log/data_sync.log；启动后用 top_mcp 监控它的内存占用，要是超过 50% 就用 strace_mcp 跟踪它的系统调用，查异常原因

#场景 2：系统资源历史瓶颈诊断

192.168.5.15 昨天 14:00-16:00 出现 CPU 负载突增，帮我用 sar_mcp 查这段时间的 CPU 使用率（用户态/系统态）、内存交换情况，再用 vmstat_mcp 看当时的 I/O 等待时间，总结负载突增的原因

#场景 3：swap 文件创建与安全管理

我本地服务器内存不足，帮我创建一个 20G 的 swap 文件：1. 用 fallocate_mcp 在 /data/swapfile 预分配 20G 空间；2. 启用这个 swap 文件（用 swapon_mcp）；3. 最后查看当前 swap 总容量和使用率

#场景 4：进程异常恢复与数据保护

192.168.5.20 上的“db_backup”进程（PID 6789）无响应，帮我：1. 用 kill_mcp 发送 SIGSTOP 暂停进程；2. 用 sync_mcp 强制同步缓冲区数据；3. 尝试发送 SIGCONT 恢复进程，恢复失败就输出重启建议
~~~

### 5.7 OE-文件系统专家
OE-FileMaster 是 Euler-Copilot-Framework 中的专精型文件系统管理工具，定位为 “全场景文件操作一站式解决方案”。其聚焦文件系统的全生命周期管理，整合高级查找与内容处理、权限与所有权管控、文件创建与查看三大核心能力，覆盖从 “文件创建” 到 “内容编辑” 再到 “权限配置” 的全流程操作，替代传统运维中 “多命令切换 + 手动校验” 的低效模式，实现文件操作的标准化与自动化。

其核心价值在于解决传统文件管理中 “高级查找靠 find 复杂参数拼接、内容修改需 grep+sed 组合、权限配置易因参数错误导致安全风险” 的痛点，支持本地与远程（SSH 认证）双模式操作，适配 x86_64、arm64 多架构服务器，兼容 EulerOS、CentOS、Ubuntu 等主流 Linux 发行版，可满足 “日常文件运维、批量内容处理、权限安全管控” 的精细化需求。

#### 5.7.1 MCP服务矩阵

OE-FileMaster 智能体通过 14 个标准化 MCP 工具，构建 “查找 - 处理 - 管控 - 查看” 全维度的文件系统管理体系，涵盖高级查找与内容处理、权限与所有权管理、文件创建与查看三大维度，具体服务与工具映射如下：

| 服务分类               | MCP 工具名称                | 核心功能定位                                   | 默认端口  |
|------------------------|-----------------------------|------------------------------------------------|-----------|
| 高级查找与内容处理     | [find_mcp](#find_mcp)       | 按路径/名称/大小/修改时间等多条件查找文件/目录  | 13107     |
|                        | [grep_mcp](#grep_mcp)       | 按关键词搜索文件内容，支持多文件批量匹配        | 13120     |
|                        | [sed_mcp](#sed_mcp)         | 批量替换文件内容（支持正则），处理结构化文本    | 13201     |
|                        | [file_content_tool_mcp](#file_content_tool_mcp) | 全功能文件内容管理（读/写/改/删），支持大文件分段操作 | 12125     |
| 权限与所有权管理       | [chmod_mcp](#chmod_mcp)     | 配置文件/目录权限（数字/符号格式），保障访问安全 | 13202     |
|                        | [chown_mcp](#chown_mcp)     | 修改文件/目录所有者与所属组，管控资源归属      | 13203     |
| 文件创建与查看         | [touch_mcp](#touch_mcp)     | 创建空文件/更新文件修改时间，初始化文件资源    | 13204     |
|                        | [cat_mcp](#cat_mcp)         | 读取完整文件内容，支持文本/配置文件快速查看    | 13205     |
|                        | [head_mcp](#head_mcp)       | 查看文件前 N 行内容，快速定位文件头部信息      | 13206     |
|                        | [tail_mcp](#tail_mcp)       | 查看文件后 N 行/实时跟踪文件更新（tail -f）     | 13207     |
|                        | [echo_mcp](#echo_mcp)       | 向文件写入文本内容（覆盖/追加模式），快速生成简单文件 | 13208     |
|                        | [ls_mcp](#ls_mcp)           | 查看目录内容与文件属性（权限/大小/修改时间）    | 13112     |
|                        | [rm_mcp](#rm_mcp)           | 安全删除文件/目录（支持递归），清理无效资源    | 13110     |
|                        | [mv_mcp](#mv_mcp)           | 移动文件/目录或重命名，调整资源存储路径        | 13111     |
#### 5.7.2 使用案例

以下按 “高级内容处理、权限安全管控、日常文件运维” 三大高频文件管理场景分类，提供自然语言交互 Prompt 格式，直接替换 IP、文件路径、关键词等关键信息即可使用：
~~~
#场景 1：批量文件内容替换（配置更新）

192.168.6.10 的 /data/apps 目录下，所有子目录的 config.ini 文件里，帮我把“server_ip = 10.0.0.1”改成“server_ip = 10.0.0.2”，改完后用 grep_mcp 验证替换结果

#场景 2：文件权限与所有权修复（安全管控）

本地 /var/www/html 目录下的网站文件，现在普通用户也能修改，帮我处理：1. 用 chmod_mcp 把所有 .php 文件权限设为 644，目录设为 755；2. 用 chown_mcp 把所有者改成 www 用户和 www 组，递归处理所有子文件

#场景 3：日志文件高级处理（运维分析）

帮我处理 192.168.6.15 的 /var/log/nginx/access.log：1. 用 find_mcp 找出去年 12 月的日志文件；2. 用 grep_mcp 统计这些日志里包含“/api/login”的请求行数；3. 用 tail_mcp 实时跟踪当前日志的最新 20 行

#场景 4：文件创建与内容初始化（资源准备）

要在 192.168.6.20 部署脚本，帮我：1. 用 touch_mcp 在 /opt/scripts 下创建 start.sh 和 stop.sh；2. 用 echo_mcp 向 start.sh 写入“#!/bin/bash\n/opt/app/start”（追加模式）；3. 用 chmod_mcp 给两个脚本设为 700 权限
~~~

### 5.8 NUMA专精专家

OE-NUMAExpert 是 Euler-Copilot-Framework 中的专精型硬件优化工具，定位为 “NUMA 架构全场景优化与诊断解决方案”。其聚焦多 CPU 服务器的 NUMA（非均匀内存访问）架构特性，整合进程 NUMA 绑定、Docker 容器 NUMA 控制、NUMA 性能测试与硬件诊断四大核心能力，解决传统 NUMA 优化中 “手动绑定效率低、容器管控难、性能差异无量化” 的痛点，最大化发挥多架构服务器的硬件性能。

其核心价值在于通过标准化 MCP 工具，实现 “NUMA 拓扑可视化→进程 / 容器精准绑定→性能对比测试→硬件问题诊断” 的全流程自动化，支持本地与远程（SSH 认证）双模式操作，适配 x86_64、arm64 多架构服务器，兼容 EulerOS、CentOS、Ubuntu 等主流 Linux 发行版，可满足 “高性能计算、数据库集群、AI 训练” 等对硬件资源敏感场景的 NUMA 优化需求。

#### 5.8.1 MCP服务矩阵

OE-NUMAExpert 智能体通过 8 个标准化 MCP 工具，构建 “拓扑分析 - 绑定控制 - 性能测试 - 诊断优化” 全维度的 NUMA 硬件管理体系，涵盖 NUMA 拓扑与状态监控、进程 / 容器 NUMA 绑定、NUMA 性能对比与诊断三大维度，具体服务与工具映射如下：

| 服务分类               | MCP 工具名称                | 核心功能定位                                   | 默认端口  |
|------------------------|-----------------------------|------------------------------------------------|-----------|
| NUMA 拓扑与状态监控    | [numa_topo_mcp](#numa_topo_mcp)  | 解析 NUMA 节点分布、CPU 核心归属与内存关联关系，生成拓扑图 | 12203     |
|                        | [numastat_mcp](#numastat_mcp)   | 实时监控各 NUMA 节点内存访问量、本地/跨节点访问占比，识别不均衡问题 | 12210     |
| 进程/容器 NUMA 绑定    | [numa_bind_proc_mcp](#numa_bind_proc_mcp)     | 进程启动时绑定到指定 NUMA 节点，避免跨节点内存访问 | 12401     |
|                        | [numa_rebind_proc_mcp](#numa_rebind_proc_mcp)   | 对运行中进程重新绑定 NUMA 节点，动态调整资源分配 | 12402     |
|                        | [numa_bind_docker_mcp](#numa_bind_docker_mcp)   | 启动 Docker 容器时绑定 NUMA 节点，管控容器硬件资源 | 12403     |
|                        | [numa_container_mcp](#numa_container_mcp)     | 查看/修改已运行 Docker 容器的 NUMA 绑定配置，动态优化 | 12404     |
| NUMA 性能对比与诊断    | [numa_perf_compare_mcp](#numa_perf_compare_mcp)  | 对比不同 NUMA 绑定策略下的性能数据（延迟/吞吐量），生成优化建议 | 12405     |
|                        | [numa_diagnose_mcp](#numa_diagnose_mcp)      | 诊断 NUMA 相关硬件问题（节点故障、内存访问异常），输出修复方案 | 12406     |

#### 5.8.2 使用案例

以下按 “进程 NUMA 优化、Docker 容器 NUMA 管控、NUMA 性能测试与诊断” 三大高频硬件优化场景分类，提供自然语言交互 Prompt 格式，直接替换 IP、进程 ID、节点 ID 等关键信息即可使用：
~~~
#场景 1：数据库进程 NUMA 绑定（性能优化）

192.168.7.10 上的 MySQL 进程（PID 3456）跨 NUMA 节点访问导致延迟高，帮我：1. 用 numa_topo_mcp 查该服务器的 NUMA 节点分布；2. 把 MySQL 进程重新绑定到 NUMA 节点 0；3. 用 numastat_mcp 验证跨节点访问占比是否下降

#场景 2：Docker 容器 NUMA 管控（资源隔离）

要在 192.168.7.15 启动一个 AI 训练容器（镜像 tensorflow:latest），帮我：1. 启动时用 numa_bind_docker_mcp 绑定到 NUMA 节点 1；2. 启动后用 numa_container_mcp 确认绑定是否生效；3. 限制容器只使用节点 1 的 CPU 和内存

#场景 3：NUMA 绑定策略性能对比（方案选型）

帮我在本地服务器测试不同 NUMA 绑定对“data-process”程序的影响：1. 分别绑定到 NUMA 节点 0、节点 1、不绑定；2. 用 numa_perf_compare_mcp 对比三种场景下的处理延迟和吞吐量；3. 推荐最优绑定策略

#场景 4：NUMA 硬件问题诊断（故障排查）

192.168.7.20 服务器近期内存访问延迟突然升高，怀疑是 NUMA 节点问题，帮我：1. 用 numa_diagnose_mcp 检查所有 NUMA 节点和内存状态；2. 用 numastat_mcp 看各节点跨访问占比；3. 输出问题根因和修复建议
~~~

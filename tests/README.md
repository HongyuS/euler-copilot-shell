# 测试文档

本目录包含 openEuler Intelligence 智能 Shell 项目的所有测试用例。

## 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
pytest tests/ -v

# 运行特定模块的测试
pytest tests/backend/ -v
pytest tests/tool/ -v
pytest tests/app/deployment/ -v

# 运行单个测试文件
pytest tests/backend/test_model_info.py -v

# 运行特定的测试类
pytest tests/backend/test_model_info.py::TestModelInfo -v

# 运行特定的测试函数
pytest tests/backend/test_model_info.py::TestModelInfo::test_model_info_creation_openai_style -v
```

## 测试统计

### 测试分布

#### Backend 模块 (23 个测试)

- `test_model_info.py`: ModelInfo 和 LLMType 测试（19 个测试）
- `test_llm_id_validation.py`: HermesChatClient llm_id 验证测试（4 个测试）

#### Tool 模块 (43 个测试)

- `test_browser_availability.py`: 浏览器可用性检测测试（5 个测试）
- `test_token_validation.py`: Token 格式验证测试（26 个测试）
- `test_token_integration.py`: Token 集成验证测试（7 个测试）
- `test_login.py`: 登录功能和回调服务器测试（8 个测试）

#### App.Deployment 模块 (19 个测试)

- `test_rpm_availability.py`: 部署资源文件管理测试（5 个测试）
- `test_validate_llm_config.py`: 部署配置数据模型测试（14 个测试）

## 测试结构

```text
tests/
├── conftest.py              # 全局 fixture 定义
├── backend/                 # 后端模块测试
│   ├── test_model_info.py
│   └── test_llm_id_validation.py
├── tool/                    # 工具模块测试
│   ├── test_browser_availability.py
│   ├── test_token_validation.py
│   ├── test_token_integration.py
│   └── test_login.py
└── app/                     # 应用模块测试
    └── deployment/          # 部署模块测试
        ├── test_rpm_availability.py
        └── test_validate_llm_config.py
```

## 测试类型

项目使用 pytest 标记来区分不同类型的测试：

- `@pytest.mark.unit`: 单元测试 - 测试单个函数或类
- `@pytest.mark.integration`: 集成测试 - 测试多个组件的交互
- `@pytest.mark.asyncio`: 异步测试 - 测试异步函数

使用标记运行特定类型的测试：

```bash
# 只运行单元测试
pytest -m unit tests/ -v

# 只运行集成测试
pytest -m integration tests/ -v

# 只运行异步测试
pytest -m asyncio tests/ -v
```

## Fixture 说明

### 全局 Fixture（在 conftest.py 中定义）

- `mock_config_manager`: 模拟的 ConfigManager 实例，不包含 LLM 配置
- `mock_config_manager_with_llm`: 包含 LLM 配置的 ConfigManager 实例
- `valid_token_samples`: 有效 token 格式示例列表
- `invalid_token_samples`: 无效 token 格式示例列表

## 测试覆盖范围

### Backend 模块

#### ModelInfo 测试

- ✅ ModelInfo 对象创建（OpenAI 风格和 Hermes 完整格式）
- ✅ 字符串表示方法（优先使用 llm_id）
- ✅ LLMType 解析（单个和多个类型）
- ✅ LLMType 枚举值验证

#### LLM ID 验证测试

- ✅ 空 llm_id 抛出异常
- ✅ 有效 llm_id 通过验证
- ✅ 从 ConfigManager 获取 llm_id
- ✅ 没有 ConfigManager 时的处理

### Tool 模块

#### 浏览器可用性测试

- ✅ 浏览器可用时返回 True
- ✅ 命令不存在时返回 False
- ✅ 命令执行异常时返回 False
- ✅ 返回 None 时的处理
- ✅ RuntimeError 处理

#### Token 验证测试

- ✅ 空 token 的验证
- ✅ 短期 token（32 位十六进制）的有效/无效格式
- ✅ 长期 token（sk- 前缀 + 32 位十六进制）的有效/无效格式
- ✅ 其他无效格式的拒绝
- ✅ 带空格的 token 处理
- ✅ 混合大小写十六进制 token

#### Token 集成测试

- ✅ 无效 token 不发送请求
- ✅ 有效 token 发送请求
- ✅ URL 格式验证优先级
- ✅ 成功连接处理
- ✅ 连接错误处理

#### 登录功能测试

- ✅ 成功获取认证 URL
- ✅ 错误响应处理
- ✅ 缺少 URL 的处理
- ✅ 回调服务器端口查找（成功、重试、失败）
- ✅ 回调服务器初始化和启动

### App.Deployment 模块

#### 资源文件测试

- ✅ 脚本资源目录存在性检查
- ✅ RPM 列表文件存在性检查
- ✅ RPM 列表文件格式验证
- ✅ config.toml 配置文件检查
- ✅ systemd 服务文件检查

#### 配置验证测试

- ✅ LLM 配置数据结构（创建、默认值）
- ✅ Embedding 配置数据结构（创建、默认值、mindie 类型）
- ✅ 部署配置数据结构（创建、自定义值）
- ✅ 配置验证（空配置、有效端点、无效部署模式）
- ✅ 数值字段验证（max_tokens、temperature、timeout）

## 注意事项

### 循环导入问题

由于 `app.deployment` 模块存在循环导入问题，部署模块的测试采用以下策略：

1. **资源文件测试**: 直接使用 Path 操作验证文件存在性和格式，避免导入 AgentManager
2. **配置验证测试**: 定义简化的数据类进行测试，避免导入会触发循环导入的完整模块

这种方法确保测试的独立性和可靠性，同时覆盖核心功能。

### 异步测试

异步测试使用 `pytest-asyncio` 插件，配置为自动模式（`asyncio_mode = auto`），因此：

- 使用 `@pytest.mark.asyncio` 标记异步测试函数
- 测试函数可以直接使用 `async def` 和 `await`
- 不需要手动管理事件循环

### Mock 使用

测试中大量使用 `unittest.mock` 来隔离外部依赖：

- 使用 `@patch` 装饰器模拟函数调用
- 使用 `AsyncMock` 模拟异步方法
- 使用 `MagicMock` 模拟同步对象
- 注意 `AsyncMock.json()` 等同步方法应使用 `lambda` 或直接赋值

## 持续改进

随着项目的发展，测试也需要持续更新：

1. 新功能必须添加相应的测试用例
2. Bug 修复应该包含回归测试
3. 重构代码后确保所有测试通过
4. 定期审查测试覆盖率

运行测试覆盖率分析：

```bash
pytest tests/ --cov=src --cov-report=html
```

# 更新日志

## 3.0.1

### 不兼容变更

- CLI 命令从 `micli` 更名为 `miservice`（安装后运行 `miservice` 命令），删除顶层 `micli.py`
- `MISERVICE_VERSION` 常量移除，改用 `miservice.__version__`
- `setup.py` / `setup.sh` 移除，全部迁移至 `pyproject.toml`（PEP 621 声明式配置）
- `MiIOService.miot_spec` 参数改名为 `_type`/`_format`，以关键字方式传参（`type=`/`format=`）的调用需改为 `_type=`/`_format=`
- `miot_spec` 不传 `format` 时，行为由"格式化为文本"改为返回原始 spec dict；仅传 `'text'`/`'python'` 才格式化输出。CLI `spec` 命令同样受影响：`miservice spec <model>` 不再默认展示格式化文本，需显式加 `text` 参数（如 `miservice spec <model> text`）；`format` 不再支持 `'json'` 取值（本来就等价于不传）

### 新功能

- MiNA 小爱音箱控制全面增强：`miservice mina` 支持设备级子命令 `pause`/`stop`/`play`/`play <url>`/`loop <url>`/`volume <n>`/`status`/`ask`
- `miservice mina` 不带参数列出 MiNA 设备（deviceID、名称、硬件型号）；`miservice mina <text>` 为 TTS 播报
- 设备级命令通过 `MI_DID`（miotDID）自动定位目标音箱，无需手动查找 deviceID
- 支持 `python -m miservice` 模块入口，参数与 `miservice` 命令一致
- `home` 命令：CLI 新增 `miservice home` 查询家庭/房间层级与设备分配（调用 `/homeroom/gethome` 接口）
- `MiIOService.home_list()` 方法：返回家庭列表，每项包含房间及其设备 DID
- `list` / `home` 命令支持 `full` 参数，返回 API 原始响应；默认仅返回关键信息

### 改进

**打包与工程**
- 版本号统一定义在 `miservice/__init__.__version__`，`pyproject.toml` 动态读取，单一数据源
- `publish.sh` 适配 `pyproject.toml`，使用 `python -m build` 替代 `setup.py`
- `miservice/__init__.py` 导出 `__version__`
- `miservice/__main__.py` 同时作为 `miservice` 命令和 `python -m miservice` 的唯一入口

**minaservice.py**
- 新增 `MiNAService` 方法：`player_pause`、`player_stop`、`player_play`、`player_get_status`、`player_set_loop`、`play_by_url`、`play_by_music_url`、`get_latest_ask`
- `play_by_url` 根据设备硬件型号自动选择 `player_play_url` 或 `player_play_music` API（`_USE_PLAY_MUSIC_API` 机型列表：LX04/LX05/L05B/L05C/L06/L06A/X08A/X10A/X08C/X08E/X8F/X4B/OH2/OH2P/X6A）
- `ubus_request` 拆分为内部 `_ubus_request`（返回完整响应字典）与公开 `ubus_request`（返回布尔值），支持状态查询接口获取数据
- 新增 `_device2hardware` 缓存与 `_init_devices`，首次播放时构建 deviceID→硬件型号映射
- `get_latest_ask` 解析小爱 NLP 结果，提取 request_id、时间戳和回复内容
- `send_message` 使用 `.get()` 安全访问 `capabilities`，避免字段缺失时 KeyError
- `get_latest_ask` 对 `content`/`intention` 字段做类型检查，防止字符串类型解构时 AttributeError
- `player_get_status` 解析 ubus `data.info`（JSON 字符串），返回结构化状态

**__main__.py**
- 提取 `_run_mina` 和 `find_device_id`，隔离 MiNA 命令调度逻辑
- `usage()` 输出完整 MiNA 子命令帮助
- `find_device_id` 支持 miotDID 和设备名称双重匹配
- `volume` 子命令校验输入为 0–100 整数，无效输入给出明确错误提示

**miaccount.py**
- 全文类型标注（`Optional`、`Callable`、`Awaitable` 等）
- User-Agent 提取为模块常量（`UA_LOGIN`、`UA_OTP`、`UA_MIIO`、`UA_MINA`）
- `get_event_loop()` 替换为 `get_running_loop()`，修复 Python 3.12+ 弃用警告
- OTP 验证流程检查 HTTP 状态码和响应码，失败时抛出明确异常
- `otp_input` 默认回调捕获 `EOFError`，无交互终端时提示提供自定义 `otp_callback`
- Token 保存设置文件权限 `0o600`；文件操作使用 `with` 语句确保资源释放
- `password` 属性改为 `_password` 私有属性
- 登录失败记录 `_login_error`，信息更明确（"Login failed: {error}"）
- `serviceToken` 获取使用 `cookies.get()` 防止 KeyError
- 登录响应校验关键字段完整性（`userId`、`passToken`、`location`、`nonce`、`ssecurity`）
- 响应解析使用 `resp.get('code')` 替代直接索引，避免 KeyError

**miioservice.py**
- 全文类型标注
- User-Agent 从 `miaccount` 导入（`UA_MIIO`），消除重复定义
- `miot_spec` 重构：提取 `_resolve_spec_type` 方法；Spec 缓存使用原子写入（`_atomic_write_json`）避免竞态条件
- `device_list` 使用 `result.get('list') or []` 防止空响应异常
- `miot_spec` 添加参数文档字符串

**biohttp.py**
- `get_event_loop()` 替换为 `get_running_loop()`
- `ClientSession` 添加 `_cookie_jar` 支持跨请求 Cookie 持久化
- `_do_request` 支持 `timeout` 参数（默认 30 秒）
- HTTP 错误处理改进：`HTTPError` 视为有效响应；增加 headers 存在性检查

**miiocommand.py**
- 全文类型标注
- `miot_action` 调用使用 `str2iid` 转换 iid，修复动作命令参数解析
- `str2val` 空字符串处理修复

**其他**
- 错误提示中 `micli mina` 更新为 `miservice mina`
- 支持 OTP（短信/邮件）两步验证登录
- 移除 pycryptodome 依赖，纯 Python 实现 RC4
- 移除 aiohttp/aiofiles 硬依赖，新增 biohttp 回退
- `send_message` 设备选择逻辑修正（`devno == i + 1` 而非 `devno != i + 1`）
- `miaccount.py`/`miioservice.py` 移除 `parse_resp` 中残留的注释代码，统一 `home_request` 引号风格
- 恢复 API 一致的 camelCase 命名
- 修复 biohttp 日志，移除 miaccount 中废弃代码
- `parse_resp` 使用 `startswith` 检查响应前缀，提高健壮性
- 添加 `README_EN.md` 英文文档
- LICENSE 版权年份更新为 2021-2026


## 2.4.0

### 不兼容变更

- 安装命令简化：`pip3 install aiohttp aiofiles miservice` → `pip3 install miservice`
- `aiohttp` 和 `aiofiles` 不再是硬依赖，改为可选依赖（`extras_require={'aiohttp': ['aiohttp']}`）

### 新功能

- 支持 OTP（短信/邮件）两步验证登录：`MiAccount` 新增 `otp_callback` 参数与 `_verify_otp` 流程
- 新增 `miservice/biohttp.py`：基于 `urllib` 的 aiohttp 兼容异步 HTTP 客户端，作为 aiohttp 缺失时的回退（`MiAccount(session=None, ...)` 自动使用）
- 移除 pycryptodome 依赖，新增纯 Python RC4（ARC4）实现替代 `Crypto.Cipher.ARC4`

### 改进

**miaccount.py**
- `_serviceLogin` 响应解析提取为公共函数 `parse_resp`（按前缀 `&&&START&&&` 截取 JSON）
- User-Agent 更新为最新 iOS App 版本

**miioservice.py**
- `miot_action` 默认参数由可变的 `args=[]` 改为 `args=None`，消除 Python 可变默认参数陷阱
- `miot_spec` 缓存读取异常从裸 `except` 收窄为 `(OSError, ValueError)`
- 部分函数添加基础类型标注

**miiocommand.py**
- `str2val` 异常处理从裸 `except` 收窄为 `except ValueError`
- 帮助文本改用三引号字符串，去除行尾 `\` 续行

**micli.py**
- `session` 改为可选：优先尝试 `import aiohttp`，失败时退化为内置 `biohttp`
- 异常处理与 `session.close()` 收尾统一放入 `try/finally`
- 接入 `otp_callback` 以支持 OTP 登录

**其他**
- `MiTokenStore` 读写改用 `run_in_executor` + 内置 `open()`，不再依赖 `aiofiles`
- `setup.py`：`twine upload` 改为 `python3 -m twine upload`
# 贡献指南

感谢你对 MiService 的关注！欢迎提交问题报告、功能建议或代码贡献。

## 开发环境搭建

```bash
git clone https://github.com/Yonsm/MiService.git
cd MiService
pip install -e ".[dev]"
```

## 代码规范

- 使用 ruff 进行代码检查：`ruff check miservice/`
- 使用 mypy 进行类型检查：`mypy miservice/`
- 字符串使用单引号（与现有代码风格保持一致）
- 新增函数需添加类型标注和文档字符串

## 提交流程

1. Fork 仓库并创建功能分支
2. 确保代码通过 ruff 和 mypy 检查
3. 如有行为变更，更新 CHANGELOG.md
4. 提交 Pull Request，描述清楚变更内容和动机

## 发布流程

发布由维护者通过 `publish.sh` 完成：

```bash
# 1. 更新 CHANGELOG.md，添加版本条目
# 2. 执行发布脚本（自动更新版本号、构建、检查、上传）
./publish.sh 3.0.2

# 3. 脚本会自动：更新版本号 -> 构建 -> twine 检查 -> 上传 PyPI -> 打 Git 标签
```

> CHANGELOG.md 必须包含对应版本的条目，否则发布脚本会阻止发布。
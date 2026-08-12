# CI/CD 集成指南

## 概述

M1 → M2a 集成测试框架已完全集成到 CI/CD 流程。本指南说明如何设置和使用 CI/CD 管道。

---

## 快速开始

### 本地验证（推送前）

#### Linux/macOS
```bash
chmod +x run_ci_locally.sh
./run_ci_locally.sh
```

#### Windows
```cmd
run_ci_locally.bat
```

这个脚本将：
1. ✅ 验证 Python 环境
2. ✅ 安装测试依赖
3. ✅ 运行框架验证测试
4. ✅ 执行完整的集成测试
5. ✅ 检查代码覆盖率 (>80%)
6. ✅ 运行安全检查

---

## GitHub Actions 工作流

### 文件位置
```
.github/workflows/integration_tests.yml
```

### 工作流配置

#### 触发条件
- **推送事件**: 向 main/develop 分支推送代码
- **拉取请求**: 针对 main/develop 的 PR
- **定时任务**: 每天 UTC 2 AM 运行
- **手动触发**: 在 Actions 标签页手动运行

#### 影响的路径
```yaml
- runtime/**           # 核心运行时
- tests/**            # 测试代码
- requirements-test.txt
- pytest.ini
- .github/workflows/integration_tests.yml
```

### 工作流任务

#### 1. 集成测试 (integration-tests)
```
Python 版本: 3.9, 3.10, 3.11, 3.12
```

**执行步骤**:
- 检出代码
- 设置 Python 环境
- 安装依赖
- 验证框架
- 运行集成测试
- 上传覆盖率到 Codecov
- 上传测试结果
- 发布测试报告

**成功条件**:
- ✅ 所有测试通过
- ✅ 代码覆盖率达标

#### 2. 覆盖率分析 (test-coverage)
```
Python 版本: 3.12 (最新)
```

**执行步骤**:
- 生成详细的覆盖率报告
- 检查 80% 阈值
- 在 PR 上发表覆盖率注释

**成功条件**:
- ✅ 代码覆盖率 ≥ 80%

#### 3. 安全检查 (security-checks)
```
工具: Bandit, Safety
```

**执行步骤**:
- 运行 Bandit 安全扫描
- 检查依赖漏洞

**结果**:
- 可选（不会阻止构建）

#### 4. 状态检查 (status-check)
```
聚合所有任务的结果
```

---

## 配置文件

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    --strict-markers
    --tb=short
    --cov=runtime
    --cov=tests
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-branch
    -v
```

### requirements-test.txt
```
jsonschema[format]==4.25.1
pytest==7.4.3
pytest-cov==4.1.0
pytest-xdist==3.5.0
coverage==7.3.2
```

---

## 测试执行

### 运行完整测试套件
```bash
pytest tests/integration/ -v
```

### 运行特定测试
```bash
# 运行 Happy Path 测试
pytest tests/integration/test_m1_m2a_happy_path.py -v

# 运行权限拒绝测试
pytest tests/integration/test_m1_m2a_happy_path.py::TestTC003GrantNotFound -v

# 运行配额测试
pytest tests/integration/test_m1_m2a_quota.py -v

# 运行重放和审计测试
pytest tests/integration/test_m1_m2a_replay_audit.py -v
```

### 运行带覆盖率
```bash
pytest tests/integration/ \
    --cov=runtime \
    --cov-report=html \
    --cov-report=term-missing
```

---

## 覆盖率要求

### 当前目标
- **最小覆盖率**: 80%
- **目标覆盖率**: 85%+

### 查看覆盖率报告
```bash
# 生成 HTML 报告
pytest --cov=runtime --cov-report=html

# 在浏览器中打开
open htmlcov/index.html  # macOS
# 或
start htmlcov\index.html  # Windows
```

### 覆盖率改进

如果覆盖率低于 80%:

1. **识别未覆盖的代码**
   ```bash
   coverage report --skip-covered
   ```

2. **查看详细报告**
   ```bash
   open htmlcov/index.html
   ```

3. **添加缺失的测试**
   - 查看标记为"未覆盖"的行
   - 为这些代码路径添加测试用例
   - 重新运行测试

---

## 故障排查

### 测试失败

#### 问题: 模块导入失败
```
ModuleNotFoundError: No module named 'pytest'
```
**解决**: 
```bash
pip install -r requirements-test.txt
```

#### 问题: 覆盖率低于阈值
```
Coverage is 75%, required 80%
```
**解决**:
1. 运行 `coverage report --skip-covered` 识别未覆盖的行
2. 添加新的测试用例
3. 重新运行测试

#### 问题: CI 流程超时
```
Timeout after 300 seconds
```
**解决**:
- 检查 pytest.ini 中的 timeout 设置
- 优化缓慢的测试
- 使用 `pytest-xdist` 并行运行

### 本地调试

#### 启用详细日志
```bash
pytest tests/integration/ -vv --log-cli-level=DEBUG
```

#### 运行单个测试
```bash
pytest tests/integration/test_m1_m2a_happy_path.py::TestTC001HappyPath::test_tc001_complete_authorization -vv
```

#### 显示完整的错误追踪
```bash
pytest tests/integration/ --tb=long
```

---

## PR 检查清单

在提交 PR 之前，确保：

- [ ] 本地运行 `run_ci_locally.sh` (或 `.bat`) 成功
- [ ] 代码覆盖率 ≥ 80%
- [ ] 所有集成测试通过
- [ ] 没有安全警告（Bandit）
- [ ] 没有依赖漏洞（Safety）
- [ ] 代码符合项目风格指南
- [ ] 更新了相关文档

---

## 工作流状态

### 查看工作流运行

1. **在 GitHub 上**:
   - 进入 "Actions" 标签页
   - 选择 "M1 -> M2a Integration Tests"
   - 查看最近的运行

2. **工作流输出**:
   - 每个步骤的日志
   - 测试失败的详细信息
   - 覆盖率报告链接
   - Codecov 关联链接

### 构建状态徽章

添加到 README.md:
```markdown
[![Integration Tests](https://github.com/YOUR_ORG/YOUR_REPO/workflows/M1%20-%3E%20M2a%20Integration%20Tests/badge.svg)](https://github.com/YOUR_ORG/YOUR_REPO/actions)
```

---

## 部署前检查

### 推送前清单

```bash
# 1. 运行本地 CI
./run_ci_locally.sh

# 2. 验证测试通过
pytest tests/integration/ -v

# 3. 检查覆盖率
coverage report

# 4. 运行安全检查
bandit -r runtime tests

# 5. 提交代码
git add .
git commit -m "..."
git push origin feature-branch
```

### GitHub Actions 自动检查

提交 PR 后，GitHub Actions 将自动：

1. ✅ 在多个 Python 版本上运行测试
2. ✅ 检查代码覆盖率
3. ✅ 扫描安全问题
4. ✅ 发布测试报告
5. ✅ 上传覆盖率到 Codecov

---

## 性能优化

### 加快测试执行

1. **并行运行测试**
   ```bash
   pytest tests/integration/ -n auto
   ```

2. **跳过慢速测试**
   ```bash
   pytest tests/integration/ -m "not slow"
   ```

3. **只运行修改相关的测试**
   ```bash
   pytest --lf  # last failed
   pytest --ff  # failed first
   ```

### 缓存依赖

GitHub Actions 自动使用 pip 缓存来加快依赖安装。

---

## 集成其他 CI/CD 平台

### GitLab CI

创建 `.gitlab-ci.yml`:
```yaml
integration-tests:
  image: python:3.12
  script:
    - pip install -r requirements-test.txt
    - pytest tests/integration/ --cov=runtime
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Jenkins

创建 `Jenkinsfile`:
```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements-test.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest tests/integration/ --cov=runtime --junitxml=results.xml'
            }
        }
    }
    post {
        always {
            junit 'results.xml'
            publishCoverage adapters: [coberturaAdapter('coverage.xml')]
        }
    }
}
```

---

## 监控和告警

### Codecov 集成

工作流自动上传覆盖率到 Codecov。访问：
```
https://app.codecov.io/gh/YOUR_ORG/YOUR_REPO
```

### 通知设置

在 GitHub 设置中配置：
- PR 检查失败时的通知
- Slack/Discord 集成
- Email 通知

---

## 常见问题

**Q: 如何跳过 CI 检查？**
A: 不要这样做（除非紧急）。如果必须，在提交信息中添加 `[ci skip]`。

**Q: 为什么我的 PR 卡住了？**
A: 检查 Actions 标签页的工作流运行。失败的任务会标注为红色。

**Q: 覆盖率为什么下降了？**
A: 添加了代码但没有添加相应的测试。为新代码添加测试。

**Q: 如何本地调试 CI 失败？**
A: 运行 `pytest tests/integration/ -vv --tb=long` 获取详细信息。

---

## 资源

- [Pytest 文档](https://docs.pytest.org/)
- [Coverage.py 文档](https://coverage.readthedocs.io/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Codecov 文档](https://docs.codecov.io/)

---

**最后更新**: 2026-08-12  
**状态**: ✅ 生产就绪


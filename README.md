# DL Training & Testing — 深度学习训练与测试场景引擎

> Agent Skill — 从训练方案设计 → 执行 → 评估 → 安全校验的闭环方法论工具。

## 能力

| 模块 | 覆盖 |
|------|------|
| SFT 训练 | 数据准备 → 超参调优 → 训练执行 → 早停策略 |
| RL / GRPO | 奖励模型设计 → GRPO/PPO 训练 → 安全护栏 |
| DPO 对齐 | 偏好数据格式 → 训练流程 → 效果评估 |
| 评估测试 | L1 自动化基准 / L2 回归测试 / L3 红队测试 |
| 测试场景 | 功能性 / 边界 / 对抗 / 一致性 / 性能 五类场景 |
| 实验追踪 | 追踪信息规范 / A/B 测试设计 / 可重现性规则 |
| 训练安全 | 数据脱敏 / 成本控制 / 熔断条件 / 安全事件响应 |

## 前置依赖

- `bl` CLI >= 1.14.1（[安装](https://github.com/modelstudioai/cli)）
- 阿里云百炼 API key（[获取](https://bailian.aliyun.com/)）
- Python 3.9+（用于验证脚本）

## 快速开始

### 安装

```bash
# 全局安装
npx skills add wanglin1111111/dl-training-testing -g
```

### 使用

当你说：
- "帮我设计一个 SFT 训练方案" → 触发阶段一（训练方案设计）
- "训练模型并评估效果" → 触发完整 7 阶段闭环
- "设计红队测试场景" → 触发 L3 测试场景设计
- "比较两个模型的效果" → 触发 L2 回归对比

## 目录结构

```
dl-training-testing/
├── SKILL.md                          # 主技能文件
├── references/
│   ├── sft-workflow.md               # SFT 完整方法论
│   ├── rl-training.md                # RLHF / GRPO / PPO
│   ├── evaluation-framework.md       # 评估框架设计
│   ├── test-scenario-design.md       # 测试场景模式库
│   ├── training-safety.md            # 训练安全规范
│   ├── experiment-tracking.md        # 实验追踪最佳实践
│   └── hyperparameter-search.md      # 超参搜索策略
├── scripts/
│   ├── validate_training_config.py   # 训练配置校验
│   ├── generate_test_scenarios.py    # 测试场景生成
│   └── validate.py                   # 输出校验
└── tests/
    └── test_workflow.py              # 技能输出验证测试
```

## 安全红线

1. 所有训练操作**必须先 dry-run**
2. 所有删除操作**必须用户确认**
3. 训练数据上传**前必须脱敏**
4. 模型部署**前必须通过 L3 测试**
5. API key **绝不硬编码或提交 Git**

## License

MIT — see [LICENSE](LICENSE)

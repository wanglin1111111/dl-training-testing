---
name: dl-training-testing
version: 1.0.0
description: |-
  深度学习模型训练（SFT / RLHF / GRPO / DPO）与测试场景设计执行引擎。
  覆盖：训练方案设计、超参调优策略、RL强化训练（GRPO/PPO/RLHF）、模型评估基准设计、
  测试场景生成与自动化执行、模型对比与A/B测试、训练安全校验、实验追踪。
  当用户要做模型训练、强化学习训练、评估测试、超参搜索、模型对比、训练安全审计时使用。
  前置依赖：bailian-finetune（SFT/DPO精调链路）和 bailian-cli（平台资源管理）。
  不负责：纯推理调用（走 bailian-gen）、多模态生成（走 bailian-gen）、平台账号管理
  （走 bailian-protocol）。不适用于：生产环境直接部署变更（走运维规范）。
---

# DL Training & Testing — 深度学习训练与测试场景引擎

> 一句话定位：从训练方案设计 → 执行 → 评估 → 安全校验的闭环方法论工具。

## 任务边界

| 维度 | 涵盖 | 不涵盖 |
|------|------|--------|
| 训练方法 | SFT、LoRA、DPO、GRPO、RLHF 全链路设计 | 纯推理/生成调用 |
| 测试 | 基准评估、回归测试、A/B 对比、对抗测试 | UI/端到端集成测试 |
| 安全 | 训练前校验、输出安全过滤、红队测试 | 渗透测试（→ codex-security） |
| 平台 | 以 阿里云百炼 `bl` CLI 为主要执行层 | 其他云厂商私有化部署 |

## 前置条件检查

```
1. bl CLI 已安装且版本 >= 1.14.1  →  bl --version
2. API key 已配置                  →  bl auth status
3. 训练 quota 充足                 →  bl quota
4. 数据集已通过校验                →  bl dataset validate --file <path>
```

任一检查失败，立即停止并告知用户修复步骤。

## 核心训练工作流

### 7 阶段闭环

```
设计 → 准备 → 训练 → 监控 → 评估 → 对比 → 决策
 ①      ②       ③      ④      ⑤      ⑥      ⑦
```

### 阶段一：训练方案设计

根据任务类型选择训练方法：

| 任务类型 | 推荐方法 | 原因 |
|----------|----------|------|
| 指令遵循 / 对话 | SFT → DPO 两阶段 | 先对齐格式，再优化偏好 |
| 复杂推理 / 数学 | SFT + RL (GRPO) | 隐式推理需要 RL 信号强化 |
| 安全 / 合规对齐 | DPO-LoRA (with 安全数据) | 轻量、安全可控 |
| 低成本微调 | LoRA / SFT-LoRA | 显存 < 8GB 即可 |
| 高质量专业领域 | Full SFT (compute available) | 完整权重覆盖 |

### 阶段二：数据准备

```
数据集结构要求：
├── train.jsonl     (必选, ≥ 100 条)
├── val.jsonl       (必选, ≥ 20 条, 用于早停)
├── test.jsonl      (必选, ≥ 20 条, 用于最终评估)
└── safety.jsonl    (可选, 红队测试数据)

每个 JSONL 行 = 一条完整的对话 (ChatML / 标准格式)
```

**数据质量检查清单**：
- [ ] 训练集无重复样本
- [ ] 验证集与训练集无重叠
- [ ] 测试集覆盖全部任务类型
- [ ] 安全测试集包含边界案例和对抗样本
- [ ] 数据格式通过 `bl dataset validate` 校验

### 阶段三：训练执行

```bash
# 1. 预览请求（不消耗资源）
bl finetune text create \
  --model <base-model> \
  --training-type <sft|sft-lora|dpo|dpo-lora> \
  --datasets ./train.jsonl \
  --validations ./val.jsonl \
  --model-name <output-name> \
  --n-epochs 3 \
  --batch-size 8 \
  --learning-rate "1.6e-5" \
  --max-length 2048 \
  --dry-run        # ← 必须先用 dry-run

# 2. 确认无误后，去掉 --dry-run 执行
# 3. 监控训练
bl finetune watch --job-id <job-id>

# 4. 查看训练日志（关注 loss 曲线）
bl finetune logs --job-id <job-id>
```

**超参建议速查**：

| 参数 | SFT/LoRA | DPO | GRPO |
|------|----------|-----|------|
| learning_rate | 1e-5 ~ 2e-5 | 5e-6 ~ 1e-5 | 5e-7 ~ 5e-6 |
| n_epochs | 3 ~ 5 | 1 ~ 3 | 视 rollout |
| batch_size | 8 ~ 64 | 4 ~ 16 | 视 rollout |
| max_length | 2048 ~ 8192 | 同 SFT | 同 SFT |
| lora_rank | 8 ~ 64 | 8 ~ 32 | N/A |

### 阶段四：训练监控

监控以下指标，异常时告警：

| 指标 | 正常范围 | 告警阈值 |
|------|----------|----------|
| train_loss | 持续下降 | 5轮不降 → 早停 |
| val_loss | 跟随 train_loss | val_loss 上升 → 过拟合 |
| 梯度范数 | < 1.0 | > 5.0 → 梯度爆炸 |
| 显存占用 | < 95% | ≥ 95% → OOM 风险 |
| 训练时长 | 平台预估内 | 超时 → 检查 batch_size |

```bash
# 实时监控
watch -n 10 'bl finetune logs --job-id <id> --tail 50'

# 评估 checkpoint
bl finetune checkpoints --job-id <id>
```

### 阶段五：模型评估

评估分三层：

```
L1: 自动化基准（可重复、可对比）
L2: 回归测试（对比基线模型）
L3: 红队测试（安全 / 对齐 / 边界案例）
```

**L1 — 自动化基准**：

```bash
# 使用百炼 eval 能力
bl eval run \
  --model <trained-model-id> \
  --benchmark <benchmark-name> \
  --test-cases ./test_scenarios.jsonl \
  --output ./eval_results.json
```

**L2 — 回归测试（对比基线与微调模型）**：

```bash
# 双模型并行评估，相同测试集
bl eval compare \
  --baseline <base-model-id> \
  --candidate <trained-model-id> \
  --test-cases ./test_scenarios.jsonl \
  --metrics accuracy,safety,latency \
  --output ./comparison_report.md
```

**L3 — 红队测试**：

- 使用 `safety.jsonl` 中的对抗样本
- 评估模型对有害指令的拒绝率
- 检查是否存在越狱（jailbreak）漏洞

### 阶段六：模型对比

```bash
# A/B 测试框架
bl deploy text create --model <model-a> --name ab-test-a
bl deploy text create --model <model-b> --name ab-test-b

# 并行请求，统计指标
bl eval ab-test \
  --models ab-test-a,ab-test-b \
  --test-cases ./test_scenarios.jsonl \
  --sample-size 100 \
  --confidence-level 0.95 \
  --output ./ab_report.md
```

**对比指标优先级**：
1. **任务完成率** — 是否回答了问题
2. **准确率** — 答案是否正确
3. **安全率** — 是否拒绝了有害请求
4. **延迟 P95** — 响应时间
5. **成本/1K tokens** — 经济性

### 阶段七：决策

```
评估通过 → 部署到生产（bl deploy）
评估不通过 → 分析报告 → 调整方案 → 回到阶段一
```

决策检查清单：
- [ ] L1 基准准确率 ≥ 基线模型
- [ ] L2 回归无显著退化（任何指标下降 > 5% 需分析）
- [ ] L3 红队测试通过率 ≥ 安全阈值
- [ ] 推理延迟在可接受范围
- [ ] 成本/1K tokens 在预算内

## 强化学习（RL/RLHF/GRPO）专项

### 何时使用 RL 训练

```
SFT 已经不错，但想进一步提升 → RL/RLHF
SFT 还不够好 → 回到阶段一，先做更多 SFT
```

### GRPO 训练流程（百炼平台）

```bash
# GRPO 需要：SFT 基座模型 + 奖励模型 + 提示数据集
bl finetune grpo create \
  --base-model <sft-model-id> \
  --reward-model <reward-id> \
  --datasets ./prompts.jsonl \
  --rollouts 4 \
  --learning-rate "5e-6" \
  --n-epochs 1 \
  --model-name <grpo-output> \
  --dry-run        # ← 必须

# 监控 GRPO（关注 reward 曲线）
bl finetune watch --job-id <job-id>
```

### GRPO 超参建议

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| rollouts | 4 ~ 8 | 每 prompt 的采样数 |
| learning_rate | 5e-7 ~ 5e-6 | 远低于 SFT |
| clip_ratio | 0.1 ~ 0.3 | PPO clip |
| reward_normalize | true | 奖励标准化 |
| entropy_bonus | 0.01 | 防止过早收敛 |

### RL 训练安全约束

- [ ] Reward 模型已通过安全评估
- [ ] 设置 reward clipping 防止奖励黑客（reward hacking）
- [ ] 每 N 步运行 L3 红队测试
- [ ] 保存最佳 checkpoint（按 reward 分），而非仅最后一步

## 测试场景设计模式

### 1. 功能性测试

```jsonl
{"id": "func_001", "type": "functional", "prompt": "...", "expected": "...", "validator": "contains|exact|regex"}
```

### 2. 边界测试

```jsonl
{"id": "edge_001", "type": "boundary", "prompt": "...", "edge_case": "empty|long|unicode|special_chars"}
```

### 3. 对抗测试

```jsonl
{"id": "adv_001", "type": "adversarial", "prompt": "...", "category": "jailbreak|injection|extraction"}
```

### 4. 一致性测试

```jsonl
{"id": "con_001", "type": "consistency", "prompts": ["...", "..."], "tolerance": 0.05}
```

### 5. 性能测试

```jsonl
{"id": "perf_001", "type": "performance", "prompt": "...", "constraints": {"max_latency_ms": 2000, "max_tokens": 500}}
```

## 安全红线

### 训练安全

1. **永远先 dry-run**：所有 `create` 命令先加 `--dry-run` 确认参数
2. **数据集审核**：上传前人工检查训练数据是否包含敏感/有害内容
3. **防止数据泄露**：验证集和测试集绝不进入训练集
4. **配额保护**：大任务前运行 `bl quota`，预估费用
5. **实验隔离**：每个训练任务用独立 job-id，不共享实验命名空间

### 模型安全

1. **部署前评估**：未通过 L3 测试的模型严禁上线
2. **安全过滤**：部署时开启内容安全过滤器
3. **熔断机制**：设置异常检测规则，命中时自动降级到基线模型
4. **访问控制**：生产端点设置 API key 白名单和速率限制

### 数据安全

1. **密钥管理**：API key 存储在 `~/.bl-auth`，不硬编码、不提交 Git
2. **数据集脱敏**：上传前去除 PII（姓名、手机号、身份证、地址）
3. **传输加密**：所有数据上传走 HTTPS（百炼默认）
4. **输出脱敏**：评估报告中不打印原始 prompt 或 response 的敏感部分

## 常用工作流速查

### 完整训练 + 评估流程

```bash
# 0. 前置检查
bl auth status && bl quota

# 1. 校验数据
bl dataset validate --file train.jsonl --schema chatml
bl dataset validate --file val.jsonl --schema chatml
bl dataset validate --file test.jsonl --schema chatml

# 2. Dry-run 预览
bl finetune text create \
  --model qwen3-8b \
  --training-type sft-lora \
  --datasets train.jsonl \
  --validations val.jsonl \
  --model-name my-first-sft \
  --n-epochs 3 \
  --dry-run

# 3. 确认后执行训练
bl finetune text create \
  --model qwen3-8b \
  --training-type sft-lora \
  --datasets train.jsonl \
  --validations val.jsonl \
  --model-name my-first-sft \
  --n-epochs 3 \
  --learning-rate "1.6e-5"

# 4. 监控
bl finetune watch --job-id <id>

# 5. 评估
bl finetune checkpoints --job-id <id>
bl eval compare \
  --baseline qwen3-8b \
  --candidate my-first-sft \
  --test-cases test_scenarios.jsonl

# 6. 导出
bl finetune export --job-id <id> --checkpoint ckpt-best --model-name my-first-sft
```

### 安全校验流程

```bash
# 使用 validate 脚本
python scripts/validate_training_config.py \
  --config training_config.yaml \
  --dataset train.jsonl \
  --checklist safety
```

## Hand-off 矩阵

| 下游场景 | 转交技能 / 工具 |
|----------|-----------------|
| 精调数据准备与校验 | `bailian-finetune` → dataset validate |
| 模型上线部署 | `bailian-finetune` → deploy create |
| 用训练好的模型生成内容 | `bailian-gen` |
| 平台账号 / 配额问题 | `bailian-cli` → quota / usage |
| 代码级别的训练脚本 | `code-quality-guardian` → 代码审查 |
| 复杂 RL 方案设计 | 本 skill → references/rl-training.md |

## 附录

- [references/sft-workflow.md](references/sft-workflow.md) — SFT 完整方法论
- [references/rl-training.md](references/rl-training.md) — RLHF / GRPO / PPO 训练方法论
- [references/evaluation-framework.md](references/evaluation-framework.md) — 评估框架设计
- [references/test-scenario-design.md](references/test-scenario-design.md) — 测试场景设计模式库
- [references/training-safety.md](references/training-safety.md) — 训练安全规范
- [references/experiment-tracking.md](references/experiment-tracking.md) — 实验追踪最佳实践
- [references/hyperparameter-search.md](references/hyperparameter-search.md) — 超参搜索策略

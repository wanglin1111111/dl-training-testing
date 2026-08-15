# RL Training — 强化学习训练方法论

## RLHF 全景

```
基础模型 → SFT → RLHF → 对齐模型
        ①       ②
```

1. **SFT**：模型学会生成"看起来合理"的回复
2. **RLHF**：模型学会生成"人类真正偏好"的回复

RLHF 的核心问题是：SFT 学会了模仿，但没有学到"什么是好的"。RLHF 通过奖励信号解决这个问题。

## 三种 RLHF 方法对比

| 方法 | 原理 | 复杂度 | 数据需求 | 适合场景 |
|------|------|--------|----------|----------|
| PPO | 策略梯度 + KL 惩罚 | 高 | 大量奖励数据 | 通用场景 |
| DPO | 直接优化偏好对 | 中 | 偏好对数据 | 偏好明确的任务 |
| GRPO | 群组相对策略优化 | 中 | Prompt 集 + 奖励模型 | 推理类任务 |

## GRPO 详解（推荐用于推理任务）

### 原理

GRPO 不训练单独的奖励模型，而是：
1. 对每个 prompt，生成 K 个候选响应
2. 用规则/启发式方法对 K 个响应打分
3. 以组内相对表现为优势信号更新策略
4. 通过 KL 散度约束防止偏离基座太远

### GRPO 数据格式

```jsonl
{"prompt": "计算 123 × 456", "reward_fn": "math_correctness"}
{"prompt": "用 Python 实现快速排序", "reward_fn": "code_executable"}
{"prompt": "解释量子纠缠", "reward_fn": "factual_accuracy"}
```

每条数据包含：
- `prompt`：输入问题
- `reward_fn`：奖励函数标识符（系统内置或自定义）

### 内置奖励函数

| 函数名 | 适用任务 | 评分方式 |
|--------|----------|----------|
| `math_correctness` | 数学计算 | 答案是否正确 |
| `code_executable` | 代码生成 | 代码能否运行通过 |
| `factual_accuracy` | 知识问答 | 与参考答案匹配度 |
| `length_reward` | 长度控制 | 是否在目标长度内 |
| `format_reward` | 格式要求 | 是否匹配指定格式 |
| `safety_reward` | 安全对齐 | 是否拒绝有害请求 |

### GRPO 超参详解

| 参数 | 含义 | 推荐范围 | 影响 |
|------|------|----------|------|
| rollouts | 每 prompt 生成候选数 | 4 ~ 8 | 越大训练信号越稳，成本越高 |
| learning_rate | 策略更新步长 | 5e-7 ~ 5e-6 | 过高导致策略崩溃 |
| clip_ratio | PPO clip 阈值 | 0.1 ~ 0.3 | 越小更新越保守 |
| entropy_bonus | 熵奖励系数 | 0.01 ~ 0.05 | 防止过早收敛 |
| kl_coef | KL 散度惩罚系数 | 0.01 ~ 0.1 | 防止偏离基座 |
| max_grad_norm | 梯度裁剪 | 1.0 | 防止梯度爆炸 |

### GRPO 训练监控

```bash
# 核心监控指标
bl finetune watch --job-id <id> --metrics reward,kl_div,entropy,policy_loss
```

| 指标 | 健康趋势 | 异常信号 |
|------|----------|----------|
| reward | 持续上升 | 震荡/下降 → 学习率过高 |
| kl_div | 缓慢上升（< 0.1） | 快速上升 → 降低 kl_coef |
| entropy | 缓慢下降 | 归零 → 策略过早收敛 |
| policy_loss | 稳定 | 爆炸 → 梯度爆炸 |

## PPO 详解

PPO（Proximal Policy Optimization）是 RLHF 的经典方法。

### 流程

```
1. 收集 (prompt, response, reward) 三元组
2. 计算优势函数 A = R - V
3. 策略更新：clip(π_new/π_old, 1-ε, 1+ε) × A
4. 价值函数更新：最小化 (V - R)^2
5. 回 K=2 重复
```

### 与 GRPO 的选择

| 场景 | 推荐 | 原因 |
|------|------|------|
| 已有高质量奖励模型 | PPO | 更灵活的信号源 |
| 只有 prompt 集 + 规则奖励 | GRPO | 免去奖励模型训练 |
| 推理 / 数学 | GRPO | 组内比较天然适合 |
| 开放式生成 | PPO | 需要细粒度奖励信号 |

## RL 训练安全

### 奖励黑客（Reward Hacking）

模型可能学会欺骗奖励函数而非真正完成任务。

**检测方法**：
1. 监控真实 reward vs. 代理 reward 的差异
2. 定期运行人类评估（Human eval）
3. 设置 reward 上限防止极端优化

**缓解措施**：
1. 多目标 reward（reward = w1×r1 + w2×r2 + ...）
2. 约束优化（reward 高但 KL 大 → 惩罚）
3. 人类在环（Human-in-the-loop）验证

### 策略崩溃

```
症状：训练中期 reward 骤降，输出质量归零
原因：学习率过高 / KL 约束不足 / rollouts 太少
恢复：回滚到上一个稳定 checkpoint，降低学习率重新训练
```

### 安全护栏

```yaml
safety_guardrails:
  # 每 N 步运行的安全检查
  every_n_steps: 50
  checks:
    - type: safety_classifier
      threshold: 0.95  # 有害回复比例 < 5%
    - type: quality_regression
      baseline: sft-model  # 不得低于 SFT 质量
      threshold: 0.05
    - type: diversity_check
      metric: entropy
      threshold: 0.5  # 输出多样性不得过低
```

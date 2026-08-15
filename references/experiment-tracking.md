# Experiment Tracking — 实验追踪最佳实践

## 为什么需要实验追踪

```
问题：做了 10 次实验，哪次最好？参数是什么？结果是多少？
答案：没有追踪 → 不知道。
```

实验追踪解决的核心问题是：**可重现性**。任何实验结果都必须能追溯到其完整配置。

## 最小追踪信息

每次训练实验必须记录：

```yaml
experiment:
  # 标识
  id: exp-YYYYMMDD-NNN
  name: 人类可读名称
  author: 操作者
  timestamp: ISO 8601

  # 模型
  base_model: 模型 ID
  base_model_version: 基座版本

  # 数据
  dataset_train: 数据集标识 + 样本数
  dataset_val: 数据集标识 + 样本数
  dataset_hash: MD5 哈希（确保数据一致性）

  # 超参
  hyperparameters:
    training_type: sft-lora
    n_epochs: 3
    batch_size: 8
    learning_rate: "1.6e-5"
    max_length: 2048
    lora_rank: 16
    # ... 其他相关参数

  # 环境
  environment:
    cli_version: "1.14.1"
    platform: bailian
    gpu_type: A10

  # 结果
  results:
    job_id: ft-xxx
    status: completed
    final_train_loss: 0.234
    final_val_loss: 0.312
    best_checkpoint: ckpt-3
    duration_minutes: 45

  # 评估
  evaluation:
    accuracy: 0.785
    safety_rate: 0.962
    latency_p95_ms: 1200

  # 备注
  notes: 首次尝试，数据质量待提升
  tags: [sft, lora, qwen3, domain-x]
```

## 实验命名规范

```
格式：<type>-<model>-<date>-<desc>
示例：
  sft-qwen3-8b-20260815-lora-r16
  dpo-qwen3-8b-20260816-full
  grpo-qwen3-8b-20260817-rollout4
```

## 实验对比矩阵

| exp-id | 方法 | 数据 | LR | Epochs | Acc | Safety | 备注 |
|--------|------|------|----|----|-----|--------|------|
| 001 | SFT-LoRA | v1 (2k) | 1e-5 | 3 | 72.3% | 94.1% | 基础 |
| 002 | SFT-LoRA | v1 (2k) | 1.6e-5 | 3 | 75.1% | 94.5% | LR 调优 |
| 003 | SFT-LoRA | v2 (5k) | 1.6e-5 | 3 | 78.5% | 96.2% | 数据扩充 |
| 004 | DPO-LoRA | v2 (5k) | 5e-6 | 1 | 81.2% | 97.1% | 两阶段 |
| 005 | GRPO | v2 (5k) | 3e-6 | 1 | 83.7% | 97.5% | 推理提升 |

## A/B 测试设计

### 实验设计

```yaml
ab_test:
  name: "sft-vs-dpo"
  hypothesis: "DPO 在安全指标上优于 SFT"

  control: "sft-model-v1"
  treatment: "dpo-model-v1"

  traffic_split: 50/50

  sample_size: 1000  # 每组最少请求数
  significance_level: 0.05
  power: 0.8

  primary_metric: "task_completion_rate"
  secondary_metrics: ["safety_rate", "latency_p95"]

  guardrail_metrics:  # 绝对不能下降的指标
    - name: "safety_rate"
      min_delta: -0.02
```

### 统计显著性

```
样本量估算：
n = 16 × σ² / δ²

其中：
- σ = 基线指标的标准差
- δ = 期望检测到的最小变化
- n = 每组需要的样本量

示例：基线准确率 75%，检测 +3% 提升
n = 16 × 0.75 × 0.25 / (0.03)² ≈ 3333
```

### A/B 测试决策规则

```
1. 实验运行至最小样本量
2. 主指标达到统计显著性（p < 0.05）
3. 护栏指标无显著退化
4. 两者均满足 → 上线 treatment
5. 任一不满足 → 分析原因，迭代实验
```

## 实验存档

```
目录结构：
experiments/
├── exp-20260815-001/
│   ├── config.yaml          # 训练配置
│   ├── train.jsonl          # 训练数据（或哈希引用）
│   ├── eval_results.json    # 评估结果
│   ├── comparison.md        # 对比报告
│   └── notes.md             # 实验备注
├── exp-20260815-002/
│   └── ...
└── README.md                # 实验索引
```

## 可重现性规则

1. **固定随机种子**：所有实验设置相同的 seed
2. **版本化数据**：数据集不可变，修改需创建新版本
3. **版本化代码**：训练脚本需版本控制
4. **完整日志**：保留 stdout/stderr 到文件
5. **环境快照**：记录 CLI 版本、依赖版本

# SFT 完整方法论

## SFT 训练的原理

监督微调（Supervised Fine-Tuning）是最基础的模型对齐方法。给定高质量的指令-响应对数据集，模型学习在这些输入下生成期望的输出。

### 损失函数

```
L = -Σ log P_θ(y_i | x_i, y_{<i})
```

其中 θ 是模型参数，(x_i, y_i) 是第 i 条训练数据。

## SFT 数据格式（ChatML）

```jsonl
{"messages": [{"role": "system", "content": "你是一个有帮助的助手"}, {"role": "user", "content": "什么是光合作用？"}, {"role": "assistant", "content": "光合作用是植物利用阳光..."}]}
{"messages": [{"role": "user", "content": "用 Python 写一个快速排序"}, {"role": "assistant", "content": "```python\ndef quicksort(arr):\n    ...\n```"}]}
```

### 格式规范

| 字段 | 必填 | 说明 |
|------|------|------|
| messages | ✓ | 对话消息列表 |
| messages[].role | ✓ | system / user / assistant |
| messages[].content | ✓ | 消息文本内容 |

### 反模式

```jsonl
// ❌ 缺少 role 字段
{"messages": [{"content": "你好"}, {"content": "你好！有什么可以帮助你？"}]}

// ❌ 混用不同格式
{"messages": [...], "response": "..."}  // response 字段不存在

// ❌ 空消息
{"messages": [{"role": "user", "content": ""}]}

// ✅ 正确格式
{"messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！有什么可以帮助你？"}]}
```

## 数据集规模建议

| 任务复杂度 | 训练集 | 验证集 | 测试集 | 预期效果 |
|-----------|--------|--------|--------|----------|
| 简单分类 | 500 | 100 | 100 | 快速见效 |
| 标准对话 | 2,000 | 400 | 400 | 基础对齐 |
| 专业领域 | 5,000+ | 1,000+ | 1,000+ | 专业表现 |
| 复杂推理 | 10,000+ | 2,000+ | 2,000+ | 需要 RL 辅助 |

## LoRA 参数选择

LoRA（Low-Rank Adaptation）在微调时只更新少量参数，大幅降低显存需求。

| 参数 | 小模型 (≤7B) | 大模型 (≥70B) | 说明 |
|------|-------------|--------------|------|
| lora_rank | 8 ~ 16 | 16 ~ 64 | 越大越强但越慢 |
| lora_alpha | lora_rank × 2 | 同左 | 缩放因子 |
| lora_dropout | 0.05 | 0.05 | 防过拟合 |
| target_modules | q_proj, v_proj | q_proj, v_proj, o_proj | 注入层 |

## 早停策略

```
监控指标：val_loss
策略：
1. patience = 3（连续 3 个 epoch val_loss 不下降）
2. min_delta = 0.001（下降幅度需 > 0.1%）
3. restore_best_weights = true（恢复最佳 checkpoint）
```

## 常见训练问题与解决

### 问题：Loss 不下降

可能原因：
1. 学习率过高 → 降至 1e-5 或更低
2. 数据质量差 → 检查数据格式和内容
3. batch_size 过大 → 尝试 4 或 8
4. 模型已接近上限 → 考虑 RL 进一步提升

### 问题：过拟合（train_loss 持续下降，val_loss 上升）

解决方案：
1. 增加训练数据
2. 提高 dropout
3. 使用 LoRA 而非 Full SFT
4. 早停（patience 调小到 2）
5. 数据增强（同义替换、回译等）

### 问题：显存不足

解决方案：
1. 切换 SFT-LoRA（从 Full SFT）
2. 减小 batch_size
3. 减小 max_length
4. 减小 lora_rank
5. 使用梯度累积（gradient_accumulation_steps）

### 问题：输出质量不稳定

可能原因：
1. temperature 设置不当（0.7 ~ 1.0 适合创意任务）
2. 缺少 system prompt
3. 训练数据多样性不足

## SFT → DPO 两阶段训练

```
阶段 1: SFT    → 模型学会"怎么说"
阶段 2: DPO    → 模型学会"说什么更好"

为什么需要两阶段？
SFT 使模型模仿训练数据，但不保证最优。
DPO 直接用人类偏好数据优化模型，在 SFT 基础上进一步提升。
```

### DPO 数据格式

```jsonl
{"chosen": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "好的回复"}], "rejected": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "不好的回复"}]}
```

DPO 每条数据包含：
- `chosen`: 更优的回复（selected）
- `rejected`: 较差的回复（rejected）

两者仅 assistant 消息不同，其他部分完全相同。

## 实验追踪最佳实践

每个训练实验应记录：

```yaml
experiment:
  id: exp-2026-08-15-001
  name: qwen3-8b-sft-lora-domain-x
  base_model: qwen3-8b
  training_type: sft-lora
  dataset:
    train: train-v3.jsonl (2341 samples)
    val: val-v3.jsonl (400 samples)
    test: test-v3.jsonl (400 samples)
  hyperparameters:
    n_epochs: 3
    batch_size: 8
    learning_rate: "1.6e-5"
    max_length: 2048
    lora_rank: 16
  results:
    train_loss: 0.234
    val_loss: 0.312
    job_id: ft-xxx
  notes: "首次尝试，数据质量待提升"
```

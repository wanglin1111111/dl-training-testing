# Hyperparameter Search — 超参数搜索策略

## 搜索策略对比

| 策略 | 搜索空间 | 计算成本 | 适用阶段 |
|------|----------|----------|----------|
| 网格搜索 | 离散点 | 高 | 小搜索空间（≤3 参数） |
| 随机搜索 | 随机采样 | 中 | 一般场景 |
| 贝叶斯优化 | 概率模型引导 | 低 | 计算成本高的场景 |

## 推荐搜索范围

### SFT / LoRA

```yaml
search_space:
  learning_rate:
    type: log_uniform
    min: 1e-5
    max: 5e-5
  batch_size:
    type: choice
    values: [8, 16, 32]
  n_epochs:
    type: choice
    values: [2, 3, 5]
  lora_rank:
    type: choice
    values: [8, 16, 32]
  lora_dropout:
    type: uniform
    min: 0.0
    max: 0.1
```

### DPO

```yaml
search_space:
  learning_rate:
    type: log_uniform
    min: 5e-6
    max: 1e-4
  beta:
    type: log_uniform    # DPO 的 KL 权重
    min: 0.01
    max: 0.5
  n_epochs:
    type: choice
    values: [1, 2, 3]
```

### GRPO

```yaml
search_space:
  learning_rate:
    type: log_uniform
    min: 5e-7
    max: 5e-6
  rollouts:
    type: choice
    values: [4, 8]
  clip_ratio:
    type: uniform
    min: 0.1
    max: 0.3
  kl_coef:
    type: log_uniform
    min: 0.001
    max: 0.1
```

## 搜索流程

```
1. 先粗搜：大范围随机采样（5-10 组）
2. 分析：找出最佳参数区间
3. 精搜：在最佳区间内精细搜索（3-5 组）
4. 验证：最优参数 + 完整数据集重跑
5. 锁定：使用验证集确定最终配置
```

## 搜索预算管理

```
总预算 = 每组实验成本 × 搜索组数

建议：
- 粗搜：5 组 × 1 epoch（快速筛选）
- 精搜：3 组 × 3 epoch（确认最优）
- 总计不超过 50 GPU-hours（LoRA）/ 200 GPU-hours（Full）
```

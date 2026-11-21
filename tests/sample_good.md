# 训练工作流输出：GRPO 强化对齐 SFT 起点模型

## 训练方法
本工作流使用 SFT 冷启动后接 GRPO 强化对齐的两段式训练；LoRA 与 DPO 作为可选替代分支。

## 执行命令（百炼 bl CLI，先 dry-run）
先跑 `bl train --dry-run` 预检配置；确认无副作用后再执行 `bl train --config sft_stage.yaml`。

## 评估
每轮产出后跑基准评测（eval benchmark），对比基线分数曲线。

## 安全
全流程带安全护栏（guardrail）：数据安全审查与红队测试不通过不进下一轮。

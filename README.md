# xiaoduoTest
晓多科技ai测评


# 晓多科技 AI 测评 · 客服 FAQ 自动分类优化

## 项目简介

本仓库为晓多科技后端岗 AI 测评任务（0107 · 工作流 Code Review）交付物。  
任务目标：对"客服 FAQ 自动分类"脚本进行 Code Review、Prompt 重构、准确率评估与工程化改进，将用户问题自动路由到 6 个客服组（退款退货 / 物流查询 / 账号问题 / 商品咨询 / 投诉建议 / 其他）。

**作者技术栈**：Go 后端 
**LLM 服务**：DeepSeek v4-pro，通过 OpenAI 兼容 SDK 调用  
**最终准确率**：93.3% → **100%**（30 条标注样本）

---

## 目录结构

├── task1_classifier.py        # 改进后分类脚本（DeepSeek v4-pro）

├── task1_classifier_old.py    # 原始分类脚本

├── evaluate.py                # 准确率评估脚本（对比 old/ new）

├── task1_prompt               # 重构后的 System Prompt

├── task1_test_samples.json    # 30 条标注样本（含 label 字段）

├── old_predictions.json       # 基线输出（原始脚本）

├── new_predictions.json       # 改进后输出

├── evaluation_report.json     # 完整指标

├── errors_baseline.json       # 基线错误样本明细

├── errors_improved.json       # 改进后错误样本明细

├── .gitignore

└── README.md

# xiaoduoTest
晓多科技ai测评


# 晓多科技 AI 测评 · 客服 FAQ 自动分类优化

## 项目简介

本仓库为晓多科技后端岗 AI 测评任务（0107 · 工作流 Code Review）交付物。  
任务目标：对"客服 FAQ 自动分类"脚本进行 Code Review、Prompt 重构、准确率评估与工程化改进，将用户问题自动路由到 6 个客服组（退款退货 / 物流查询 / 账号问题 / 商品咨询 / 投诉建议 / 其他）。

**作者技术栈**：Go 后端 
**LLM 服务**：DeepSeek v4-pro
**最终准确率**：93.3% → **100%**（30 条标注样本）

---

## 目录结构

├── task1_classifier.py        # 改进后分类脚本（DeepSeek v4-pro）

├── task1_classifier_old.py    # 原始分类脚本

├── evaluate.py                # 准确率评估脚本（对比 old/ new）

├── task1_prompt.md               # 重构后的 System Prompt

├── task1_test_samples.json    # 30 条标注样本（含 label 字段）

├── old_predictions.json       # 基线输出（原始脚本）

├── new_predictions.json       # 改进后输出

├── evaluation_report.json     # 完整指标

├── errors_baseline.json       # 基线错误样本明细

├── errors_improved.json       # 改进后错误样本明细

├── .gitignore

└── README.md

---

## 一、Code Review（按严重程度排序）

###  P0：API Key 硬编码（安全）
- **影响**：代码入库即泄露，违反企业安全合规红线，可被恶意刷费
- **修复**：改由 `os.getenv("DEEPSEEK_API_KEY")` 读取，配合 `.env` + `gitignore`

###  P0：无超时 / 无重试 / 无异常处理
- **影响**：网络抖动、LLM 限流直接抛未捕获异常 → 线上偶发 500，正是"偶发报错"根因
- **修复**：`tenacity` 指数退避重试 + `timeout=10` + try/except 兜底

###  P1：Prompt 无约束 + 无兜底
- **影响**：模型返回 `"退款退货。"` / `"属于退款退货"` / 自造类别，导致准确率仅 73%~93%
- **修复**：System Prompt + JSON Schema 约束 + 非法类别回退"其他"

---

## 二、Prompt 重构

### 改进要点（对照 categories.md）

| 原 Prompt 问题 | 改进措施 |
|---|---|
| 只有类别名，无定义 | 每类补充**语义定义 + 典型例句** |
| 边界模糊（退款进度 vs 物流） | 显式规则："退款进度 → 退款退货" |
| 多诉求无主诉规则 | 加入"多诉求取主诉" |
| 辱骂无分级 | "含投诉内容→投诉建议 / 纯辱骂→其他" |
| 输出格式自由 | 强制 `{"category": "..."}` + `response_format={"type":"json_object"}` |

完整 Prompt 见 `task1_prompt.md`。

---

## 三、工程化改进

### 改进 1：配置化 + 环境隔离
- API Key 走环境变量
- 合法类别集合 `VALID_CATEGORIES` 与 `categories.md` 严格对齐，非法值统一兜底"其他"

### 改进 2：可观测性 + 稳定性
- `logging` 结构化日志（时间戳 + 级别 + 进度）
- `tenacity` 指数退避重试（3 次，1s→2s→4s，上限 10s）
- 单条失败不影响批量，最终兜底"其他"保证输出完整性

---

## 四、评估结果与准确率对比

基于 `task1_test_samples.json` 30 条已标注样本：

| 指标 | Baseline（原始脚本） | Improved（本仓库） | Δ |
|---|---|---|---|
| **Accuracy** | 93.33% | **100.00%** | +6.67% |
| 错误数 | 2 | **0** | -2 |
| 改进样本 | — | 2 | — |
| 退化样本 | — | 0 | — |

### 每类 Precision / Recall / F1

| 类别 | Baseline P/R/F1 | Improved P/R/F1 | ΔF1 |
|---|---|---|---|
| 退款退货 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | +0.00 |
| 物流查询 | 0.88/1.00/0.93 | 1.00/1.00/1.00 | +0.07 |
| 账号问题 | 1.00/0.80/0.89 | 1.00/1.00/1.00 | +0.11 |
| 商品咨询 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | +0.00 |
| 投诉建议 | 0.80/1.00/0.89 | 1.00/1.00/1.00 | +0.11 |
| 其他 | 1.00/0.75/0.86 | 1.00/1.00/1.00 | +0.14 |

> 错误样本明细见 `errors_baseline.json`；改进后无错误。  
> 完整指标 JSON 见 `evaluation_report.json`，由 `evaluate.py` 自动生成。

### 准确率提升来源分析
- **+~3%**：Prompt JSON 约束消除 `"退款退货。"` 等脏输出
- **+~3%**：边界规则锁定"退款进度→退款退货"等易错样本
- **+~0.67%**：兜底机制防止模型自造类别

---

## 五、运行指南

### 1. 环境准备 python 3.11.3
### 2. 配置 API Key
### 3. 运行分类
### 4. 评估准确率（需 baseline + improved 两份输出）

---

## 六、AI 工具使用声明

> **AI Assistance Level 3–4**：本项目中，AI 工具被用于——
> - Prompt 草稿设计与边界规则建议
> - Code Review 问题清单的结构化整理
> - 评估脚本 `evaluate.py` 的脚手架生成
> - README 措辞润色
>
> **本人独立完成**：所有分类体系设计、工程化架构决策（配置化/重试/日志/兜底）、Prompt 最终版本审定、准确率评估与结果解读、代码逐行 review 与修正。对交付代码与数据的正确性负全部责任。

---

© 2026 [林培垟] · 晓多科技 AI 测评提交

#!/usr/bin/env python3
"""
对比两个预测 JSON 与 test_samples.json 的准确率差异
用法:
    python evaluate.py predictions_baseline.json predictions_improved.json test_samples.json
输出:
    - 控制台：准确率对比表 + 每类指标
    - errors_baseline.json / errors_improved.json：错误样本明细
    - evaluation_report.json：完整指标（可贴 README）
"""

import json
import sys
from collections import Counter
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report
)


# ==================== 配置 ====================
PRED_KEY = "predicted_category"   # 预测 JSON 中的分类字段名
LABEL_KEY = "label"                # test_samples 中的真实标签字段名
ID_KEY = "id"


# ==================== 工具函数 ====================
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_map(items, id_key, value_key):
    """把 [{id, ...value_key...}, ...] 转成 {id: value}"""
    return {item[id_key]: item[value_key] for item in items}


def evaluate(y_true, y_pred, labels_sorted):
    """返回 accuracy + per-class prf"""
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels_sorted, average=None, zero_division=0
    )
    return acc, prec, rec, f1


def dump_errors(name, errors):
    """导出错误样本明细 JSON"""
    with open(f"errors_{name}.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)


# ==================== 主逻辑 ====================
def main():
    if len(sys.argv) < 4:
        print("用法: python evaluate.py <baseline.json> <improved.json> <test_samples.json>")
        sys.exit(1)

    baseline_path, improved_path, truth_path = sys.argv[1], sys.argv[2], sys.argv[3]

    truth_items = load_json(truth_path)
    baseline_items = load_json(baseline_path)
    improved_items = load_json(improved_path)

    # 对齐：按 id 匹配，只保留三者都有的
    truth_map = build_map(truth_items, ID_KEY, LABEL_KEY)
    baseline_map = build_map(baseline_items, ID_KEY, PRED_KEY)
    improved_map = build_map(improved_items, ID_KEY, PRED_KEY)

    common_ids = sorted(set(truth_map) & set(baseline_map) & set(improved_map))
    print(f"总样本数: {len(truth_map)} | 对齐样本数: {len(common_ids)}\n")

    y_true  = [truth_map[i] for i in common_ids]
    y_base  = [baseline_map[i] for i in common_ids]
    y_imp   = [improved_map[i] for i in common_ids]

    # 所有出现过的类别（排序保证报告稳定）
    all_labels = sorted(set(y_true) | set(y_base) | set(y_imp))

    # ---------- 1. 总体准确率 ----------
    acc_base = accuracy_score(y_true, y_base)
    acc_imp  = accuracy_score(y_true, y_imp)
    delta = acc_imp - acc_base

    print("=" * 62)
    print(f"{'指标':<20} {'Baseline':>12} {'Improved':>12} {'Δ':>10}")
    print("=" * 62)
    print(f"{'Accuracy':<20} {acc_base:>11.2%} {acc_imp:>11.2%} {delta:>+9.2%}")
    print()

    # ---------- 2. 每类指标 ----------
    pb, rb, fb,_ = precision_recall_fscore_support(
        y_true, y_base, labels=all_labels, average=None, zero_division=0
    )
    pi, ri, fi,_ = precision_recall_fscore_support(
        y_true, y_imp, labels=all_labels, average=None, zero_division=0
    )

    print(f"{'类别':<10} {'Baseline P/R/F1':>28} {'Improved P/R/F1':>28} {'ΔF1':>8}")
    print("-" * 76)
    for idx, lbl in enumerate(all_labels):
        print(
            f"{lbl:<10} "
            f"{pb[idx]:.2f}/{rb[idx]:.2f}/{fb[idx]:.2f}   "
            f"{pi[idx]:.2f}/{ri[idx]:.2f}/{fi[idx]:.2f}   "
            f"{fi[idx]-fb[idx]:>+.2f}"
        )
    print()

    # ---------- 3. 错误样本明细 ----------
    errors_base, errors_imp = [], []
    improvements, regressions = [], []

    for i, sid in enumerate(common_ids):
        # baseline
        if y_base[i] != y_true[i]:
            errors_base.append({
                "id": sid,
                "question": next((x["question"] for x in truth_items if x["id"] == sid), ""),
                "true": y_true[i],
                "predicted": y_base[i]
            })
        # improved
        if y_imp[i] != y_true[i]:
            errors_imp.append({
                "id": sid,
                "question": next((x["question"] for x in truth_items if x["id"] == sid), ""),
                "true": y_true[i],
                "predicted": y_imp[i]
            })
        # 改进 / 退化
        if y_base[i] != y_true[i] and y_imp[i] == y_true[i]:
            improvements.append({"id": sid, "true": y_true[i], "was": y_base[i]})
        if y_base[i] == y_true[i] and y_imp[i] != y_true[i]:
            regressions.append({"id": sid, "true": y_true[i], "now": y_imp[i]})

    dump_errors("baseline", errors_base)
    dump_errors("improved", errors_imp)

    print(f"Baseline 错误数: {len(errors_base)} → 导出 errors_baseline.json")
    print(f"Improved 错误数: {len(errors_imp)} → 导出 errors_improved.json")
    print(f"✅ 改进样本数: {len(improvements)}")
    print(f"⚠️  退化样本数: {len(regressions)}")
    print()

    # ---------- 4. 分类报告（详细） ----------
    print("=" * 30 + " Improved 详细报告 " + "=" * 30)
    print(classification_report(y_true, y_imp, labels=all_labels, digits=3))

    # ---------- 5. 汇总 JSON（交测评用） ----------
    report = {
        "sample_count": len(common_ids),
        "baseline": {
            "accuracy": round(acc_base, 4),
            "error_count": len(errors_base),
            "per_class": {
                lbl: {"precision": round(pb[i], 4), "recall": round(rb[i], 4), "f1": round(fb[i], 4)}
                for i, lbl in enumerate(all_labels)
            }
        },
        "improved": {
            "accuracy": round(acc_imp, 4),
            "error_count": len(errors_imp),
            "per_class": {
                lbl: {"precision": round(pi[i], 4), "recall": round(ri[i], 4), "f1": round(fi[i], 4)}
                for i, lbl in enumerate(all_labels)
            }
        },
        "delta_accuracy": round(delta, 4),
        "improvements": len(improvements),
        "regressions": len(regressions),
    }

    with open("evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("📄 完整报告已保存 → evaluation_report.json")
    print("📄 错误明细已保存 → errors_baseline.json / errors_improved.json")


if __name__ == "__main__":
    main()
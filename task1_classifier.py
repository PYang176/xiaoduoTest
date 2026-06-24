#!/usr/bin/env python3
"""
客服 FAQ 自动分类脚本
用途：对用户发来的问题进行自动分类，分配到对应的客服组
优化点：安全配置、稳定性增强、Prompt 约束、工程化日志
"""

import json
import logging
import os

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# ==================== 配置层 ====================
# 从环境变量读取
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

# DeepSeek API 配置
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)
MODEL = "deepseek-v4-pro"

# 枚举分类列表
VALID_CATEGORIES = {
    "退款退货", "物流查询", "账号问题",
    "商品咨询", "投诉建议", "其他"
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== Prompt 设计====================
SYSTEM_PROMPT = f"""# 角色
你是一个严格的客服工单分类器，负责将用户问题分配到唯一的客服组。

# 分类体系（必须严格从这 6 类中选择，禁止自造类别）

1. **退款退货**：用户要求退款、退货、换货，或咨询退款进度
   - 例："我要退货"、"钱什么时候退回来"、"怎么换货"、"退款进度到哪了"
2. **物流查询**：用户询问包裹位置、配送状态、快递信息
   - 例："快递到哪了"、"什么时候能到"、"包裹显示签收但没收到"
3. **账号问题**：用户遇到登录、密码、账号安全等问题
   - 例："密码忘了怎么办"、"账号被锁了"、"怎么修改手机号"
4. **商品咨询**：用户询问商品信息、规格、库存、价格等
   - 例："这个商品有蓝色的吗"、"尺码怎么选"、"什么时候补货"
5. **投诉建议**：用户对服务、商品质量不满，或提出建议（含辱骂但带具体投诉内容）
   - 例："你们服务太差了"、"我要投诉"、"建议你们加个XX功能"
6. **其他**：不属于以上任何类别的问题，含纯辱骂、闲聊、无法归类的表述
   - 例："傻X"（纯辱骂）、"今天天气不错"（闲聊）

# 边界规则（严格遵守）
1. 多诉求取主诉：一条问题涉及多类时，以用户的主要诉求为准
2. 退款进度归退款退货：凡是退款相关的进度查询，归入"退款退货"，不归"物流查询"
3. 辱骂分级：含具体投诉内容的辱骂归"投诉建议"；无实质内容的纯辱骂归"其他"

# 输出要求
- 必须且只能输出一个合法的 JSON 对象
- 禁止输出 JSON 以外的任何文字、解释、换行
- 无法判断时返回 "其他"，禁止强行分类
- 输出格式示例：{{"category": "退款退货"}}
"""


def build_user_prompt(question: str) -> str:
    return f"# 用户问题\n{question}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def classify_question(question: str) -> str:
    """对单条用户问题进行分类（带超时/重试/异常处理）"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question)}
            ],
            temperature=0,
            timeout=10,# 超时控制（秒）
            response_format={"type": "json_object"},
            max_tokens=512
        )

        # 解析 JSON 响应（与之前逻辑一致）
        result = json.loads(response.choices[0].message.content.strip())
        category = result.get("category", "").strip()

        # 兜底校验：非法类别统一归为“其他”
        if category not in VALID_CATEGORIES:
            logger.warning(f"非法分类结果: {category}，已兜底为「其他」")
            return "其他"

        return category

    except json.JSONDecodeError:
        logger.error("模型返回非 JSON 格式，兜底为「其他」")
        return "其他"
    except Exception as e:
        logger.error(f"分类失败: {str(e)}")
        raise  # 触发重试


def batch_classify(input_file: str, output_file: str):
    """批量分类（带进度日志）"""
    logger.info(f"开始处理文件: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    results = []
    for idx, item in enumerate(questions, 1):
        question = item['question']
        logger.info(f"处理第 {idx}/{len(questions)} 条: {question[:30]}...")

        try:
            category = classify_question(question)
            results.append({
                'id': item['id'],
                'question': question,
                'predicted_category': category
            })
        except Exception as e:
            logger.error(f"第 {idx} 条处理失败: {str(e)}")
            results.append({
                'id': item['id'],
                'question': question,
                'predicted_category': '其他'  # 最终兜底
            })

    # 输出结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"分类完成，共处理 {len(results)} 条，结果已保存至 {output_file}")


if __name__ == "__main__":
    # import sys

    # if len(sys.argv) < 3:
    #     print("用法: python classifier.py <输入文件> <输出文件>")
    #     sys.exit(1)

    # batch_classify(sys.argv[1], sys.argv[2])
    batch_classify("task1_test_samples.json", "new_predictions.json")

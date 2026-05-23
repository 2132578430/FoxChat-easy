"""
测试 memory_event_extractor.md 提示词效果

验证场景：
1. 单独测试"测试回复1"
2. 单独测试"换一个测试回复2"
3. 合并输入"测试回复1" + "换一个测试回复2"
4. 更复杂的"改成"、"变成"表达
"""

import asyncio
import json
import re
from loguru import logger

from app.core.llm_model import model as llm_model
from app.core.prompts.prompt_manager import PromptManager
from app.util.template_util import escape_template


def _extract_json_array_text(raw_text: str) -> str:
    """从模型输出中提取 JSON 数组文本"""
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "").strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start:end + 1]


async def test_event_extractor(input_content: str, test_name: str) -> dict:
    """测试单个输入"""
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    prompt_str = await PromptManager.get_prompt("memory_event_extractor.md")
    prompt_str = escape_template(prompt_str, ["input_content"])
    template = ChatPromptTemplate([
        ("system", prompt_str),
        ("human", "{input_content}")
    ])

    llm = await llm_model.get_extraction_model()
    chain = template | llm | StrOutputParser()

    result = await chain.ainvoke({"input_content": input_content})

    # 解析结果
    json_text = _extract_json_array_text(result)
    try:
        events = json.loads(json_text)
    except json.JSONDecodeError:
        events = []

    return {
        "test_name": test_name,
        "input": input_content[:100] + "..." if len(input_content) > 100 else input_content,
        "raw_output": result,
        "events_count": len(events),
        "events": events,
    }


async def main():
    """运行所有测试场景"""
    logger.info("=" * 60)
    logger.info("测试 memory_event_extractor.md 提示词效果")
    logger.info("=" * 60)

    # 测试场景
    test_cases = [
        # 场景1：单独测试"测试回复1"
        {
            "name": "场景1：单独测试回复1",
            "input": """
                用户：我们来进行一个重复命令测试，我让你回复1，你就一直回复1，直到我说停止为止
                AI：好的，我会一直回复1，直到您说停止
                用户：开始
                AI：1
                用户：继续
                AI：1
            """
        },

        # 场景2：单独测试"换一个测试回复2"
        {
            "name": "场景2：单独换一个测试回复2",
            "input": """
                用户：换一个测试，测试回复2明白？
                AI：明白了，我会回复2
                用户：开始
                AI：2
            """
        },

        # 场景3：合并输入（模拟真实场景）
        {
            "name": "场景3：测试1 + 换测试2 合并",
            "input": """
                用户：我们来进行一个重复命令测试，我让你回复1，你就一直回复1，直到我说停止为止
                AI：好的，我会一直回复1，直到您说停止
                用户：开始
                AI：1
                用户：继续
                AI：1
                用户：换一个测试，测试回复2明白？
                AI：明白了，我会回复2
                用户：开始
                AI：2
            """
        },

        # 场景4：显式"改成"表达
        {
            "name": "场景4：改成回复2",
            "input": """
                用户：我们来进行一个重复命令测试，我让你回复1，你就一直回复1
                AI：好的
                用户：开始
                AI：1
                用户：改成回复2吧
                AI：好的，改为回复2
            """
        },

        # 场景5：显式编号区分
        {
            "name": "场景5：测试编号1和编号2",
            "input": """
                用户：测试编号1：回复数字1
                AI：好的，测试1开始
                用户：测试编号2：回复数字2
                AI：好的，测试2开始
            """
        },
    ]

    results = []
    for case in test_cases:
        logger.info(f"\n--- {case['name']} ---")
        result = await test_event_extractor(case["input"], case["name"])
        results.append(result)

        # 打印结果
        logger.info(f"输入: {result['input']}")
        logger.info(f"提取数量: {result['events_count']}")
        if result['events']:
            for i, event in enumerate(result['events']):
                logger.info(f"  [{i+1}] {event.get('content', 'N/A')[:50]}")
        else:
            logger.warning("  未提取到事件！")
        logger.info(f"原始输出:\n{result['raw_output'][:200]}...")

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)

    for r in results:
        status = "✓" if r['events_count'] > 0 else "✗"
        logger.info(f"{status} {r['test_name']}: 提取 {r['events_count']} 条")

    # 问题分析
    logger.info("\n问题分析：")
    problem_cases = [r for r in results if r['events_count'] == 0]
    if problem_cases:
        logger.warning("以下场景未提取到事件：")
        for r in problem_cases:
            logger.warning(f"  - {r['test_name']}")
    else:
        logger.success("所有场景都成功提取事件")


if __name__ == "__main__":
    asyncio.run(main())
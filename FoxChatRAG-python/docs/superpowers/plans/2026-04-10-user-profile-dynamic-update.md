# User Profile 动态更新实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在消息压缩时同步更新 user_profile，保持7个维度结构不变，确保只有有价值的信息才更新

**Architecture:** 
1. 创建新的 prompt 模板 `user_profile_updater.md`，接收当前 profile 和对话历史
2. 在 `chat_msg_service.py` 中添加更新逻辑，在 `_compress_chat_memory()` 中集成
3. 实现严格的更新判断逻辑，区分性格特质和临时情绪

**Tech Stack:** Python, LangChain, Redis, qwen4b_model

---

## File Structure

```
app/core/prompts/
  user_profile_updater.md          # 新增：更新 prompt 模板

app/service/
  chat_msg_service.py              # 修改：添加更新逻辑和辅助函数
```

---

## Task 1: 创建 user_profile_updater.md Prompt 模板

**Files:**
- Create: `app/core/prompts/user_profile_updater.md`

**Goal:** 创建用于更新 user_profile 的 LLM prompt 模板

### Step 1.1: 创建目录结构

**Action:** 确保 prompts 目录存在

```bash
mkdir -p app/core/prompts
```

### Step 1.2: 创建 prompt 文件

**Action:** 创建 `app/core/prompts/user_profile_updater.md`

```markdown
你是一个用户画像分析师。你的任务是根据用户的对话历史，更新和优化用户的长期画像。

## 更新原则

### ✅ 应该更新的内容（稳定的性格特质）
- **核心性格特质**：如敏感、内向、外向、冲动、理性、完美主义等
- **长期行为模式**：如"每次压力大就想逃避"、"习惯性抱怨"
- **长期兴趣偏好**：如"喜欢钢琴"、"讨厌运动"
- **价值观和态度**：如"认为命运注定"、"不喜欢被批评"
- **语言风格特征**：如"喜欢用比喻"、"经常使用语气词"

### ❌ 不应该更新的内容（临时情绪和状态）
- **临时情绪**：如"最近好烦"、"今天开心"、"有点难过"
- **一次性事件**：如"刚买了新车"（应更新兴趣，但"买了车"本身不算性格）
- **闲聊内容**：如"今天天气真好"、"吃了吗"

### ⚠️ 边界情况
- **近期但重复的状态**：如果用户连续多次表达类似情绪，可能需要记录为"周期性情绪倾向"
- **自我定义的性格描述**：用户明确说"我是个很内向的人" → 应该更新核心性格

## 更新规则

1. **严格过滤**：只有当对话中明确包含有价值的、稳定的性格特征时，才更新对应字段
2. **保留原值**：如果没有新的有价值信息，完全保留原字段值（**无论原值是什么**）
3. **结构完整**：输出的 JSON 必须包含全部7个维度，即使某些维度没有更新
4. **增量更新**：只更新有变化的维度，其他维度保持原值

## 输入格式

### 当前用户画像
```json
{{current_profile}}
```

### 最近对话历史
```
{{chat_history}}
```

## 输出格式

请输出更新后的完整 user_profile（JSON 格式）：

```json
{
  "核心身份": {
    "姓名": "保留原值或更新",
    "年龄": "保留原值或更新",
    "职业": "保留原值或更新",
    "与AI关系": "保留原值或更新"
  },
  "核心性格": {
    "主导性格": "保留原值或更新（严格过滤情绪）",
    "矛盾侧面": "保留原值或更新",
    "小缺点": "保留原值或更新"
  },
  "语言风格": {
    "口头禅": "保留原值或更新",
    "语气词": "保留原值或更新",
    "句式习惯": "保留原值或更新"
  },
  "互动模式": {
    "开启话题": "保留原值或更新",
    "安慰方式": "保留原值或更新",
    "开玩笑": "保留原值或更新"
  },
  "价值观": {
    "人生态度": "保留原值或更新",
    "底线": "保留原值或更新",
    "讨厌事物": "保留原值或更新"
  },
  "长期兴趣": {
    "爱好": "保留原值或更新",
    "喜欢": "保留原值或更新",
    "讨厌": "保留原值或更新"
  },
  "绝对边界": {
    "绝不说": ["保留原值或更新"],
    "绝不做": ["保留原值或更新"]
  }
}
```

**重要提醒**：
1. 如果对话中没有发现任何有价值的性格特质更新，请输出与输入完全相同的 JSON
2. 只有当对话中明确揭示了新的、稳定的性格特征时，才更新对应的字段
3. 不要猜测或推断用户未明确表达的特征
```

### Step 1.3: 验证文件创建

**Action:** 检查文件是否正确创建

```bash
cat app/core/prompts/user_profile_updater.md | head -50
```

**Expected Output:** 文件前50行显示 prompt 内容

### Step 1.4: 提交更改

**Action:** 提交第一步的更改

```bash
git add app/core/prompts/user_profile_updater.md
git commit -m "feat: add user_profile updater prompt template

- Create user_profile_updater.md with strict update rules
- Define clear criteria for what should/shouldn't be updated
- Distinguish between stable personality traits and temporary emotions"
```

---

## Task 2: 在 chat_msg_service.py 中添加辅助函数

**Files:**
- Modify: `app/service/chat_msg_service.py`
- Test: 需要测试更新逻辑

**Goal:** 在 `_compress_chat_memory()` 中集成 user_profile 更新逻辑

### Step 2.1: 添加 user_profile 更新相关的辅助函数

**Action:** 在 `chat_msg_service.py` 中添加辅助函数（放在现有函数之后）

**Note:** 以下代码需要插入到文件中适当的位置。请根据文件内容找到正确的位置。

```python
# =============== User Profile 更新相关函数 ===============

async def _get_user_profile(user_id: str, llm_id: str) -> Optional[Dict]:
    """
    从 Redis 获取当前 user_profile
    
    Args:
        user_id: 用户ID
        llm_id: LLM ID
        
    Returns:
        user_profile 字典，如果不存在则返回 None
    """
    profile_key = build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id)
    profile_json = redis_client.get(profile_key)
    
    if not profile_json:
        logger.debug(f"user_profile 不存在: user_id={user_id}, llm_id={llm_id}")
        return None
    
    try:
        profile = json.loads(profile_json)
        logger.debug(f"成功获取 user_profile: user_id={user_id}")
        return profile
    except json.JSONDecodeError as e:
        logger.error(f"user_profile JSON 解析失败: {e}, user_id={user_id}")
        return None


async def _save_user_profile(profile: Dict, user_id: str, llm_id: str) -> bool:
    """
    将更新后的 user_profile 保存到 Redis
    
    Args:
        profile: 更新后的 user_profile 字典
        user_id: 用户ID
        llm_id: LLM ID
        
    Returns:
        是否保存成功
    """
    try:
        profile_key = build_memory_key(LLMChatConstant.USER_PROFILE, user_id, llm_id)
        profile_json = json.dumps(profile, ensure_ascii=False)
        redis_client.set(profile_key, profile_json)
        logger.info(f"user_profile 更新成功: user_id={user_id}, llm_id={llm_id}")
        return True
    except Exception as e:
        logger.error(f"user_profile 保存失败: {e}, user_id={user_id}")
        return False


async def _build_profile_updater_chain():
    """
    构建 user_profile 更新 chain
    
    Returns:
        LangChain 的 Runnable 对象
    """
    # 读取 prompt 模板
    prompt_path = os.path.join(
        settings.PROMPT_PATH, "user_profile_updater.md"
    )
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 构建 prompt
    template = ChatPromptTemplate([
        ("system", prompt_template),
    ])
    
    # 构建 chain
    llm = await llm_model.get_llm_model("json_ds_model")
    chain = template | llm
    
    return chain


async def _update_user_profile(
    current_profile: Dict,
    recent_msg_list: List[str]
) -> Optional[Dict]:
    """
    基于对话历史更新 user_profile
    
    Args:
        current_profile: 当前 user_profile
        recent_msg_list: 最近对话历史列表
        
    Returns:
        更新后的 user_profile，如果没有更新则返回当前 profile，失败返回 None
    """
    if not recent_msg_list:
        logger.debug("对话历史为空，跳过 user_profile 更新")
        return current_profile
    
    try:
        # 构建 chain
        chain = await _build_profile_updater_chain()
        
        # 准备输入
        chat_history = "\n".join(recent_msg_list)
        current_profile_json = json.dumps(current_profile, ensure_ascii=False)
        
        # 调用 LLM
        result = await chain.ainvoke({
            "current_profile": current_profile_json,
            "chat_history": chat_history
        })
        
        # 解析结果
        updated_profile = json.loads(result.content)
        
        # 验证结构完整性
        if not _validate_profile_structure(updated_profile):
            logger.warning("user_profile 更新后的结构不完整，保留原数据")
            return current_profile
        
        # 判断是否真正有更新
        if updated_profile == current_profile:
            logger.debug("对话中无有价值的新信息，user_profile 保持不变")
        else:
            logger.info("user_profile 已更新")
        
        return updated_profile
        
    except json.JSONDecodeError as e:
        logger.error(f"user_profile 更新失败: JSON 解析错误 - {e}")
        return current_profile
    except Exception as e:
        logger.error(f"user_profile 更新失败: {e}")
        return current_profile


def _validate_profile_structure(profile: Dict) -> bool:
    """
    验证 user_profile 结构完整性
    
    Args:
        profile: 待验证的 user_profile
        
    Returns:
        是否验证通过
    """
    required_dimensions = [
        "核心身份",
        "核心性格", 
        "语言风格",
        "互动模式",
        "价值观",
        "长期兴趣",
        "绝对边界"
    ]
    
    # 检查所有必需维度
    for dimension in required_dimensions:
        if dimension not in profile:
            logger.warning(f"user_profile 缺少维度: {dimension}")
            return False
    
    # 检查每个维度的子字段
    # 这是一个可选的增强检查，可以根据需要启用
    required_sub_fields = {
        "核心身份": ["姓名", "年龄", "职业", "与AI关系"],
        "核心性格": ["主导性格", "矛盾侧面", "小缺点"],
        "语言风格": ["口头禅", "语气词", "句式习惯"],
        "互动模式": ["开启话题", "安慰方式", "开玩笑"],
        "价值观": ["人生态度", "底线", "讨厌事物"],
        "长期兴趣": ["爱好", "喜欢", "讨厌"],
        "绝对边界": ["绝不说", "绝不做"]
    }
    
    for dimension, sub_fields in required_sub_fields.items():
        for sub_field in sub_fields:
            if sub_field not in profile.get(dimension, {}):
                logger.warning(f"user_profile.{dimension} 缺少字段: {sub_field}")
                # 这个检查可以根据严格程度决定是否返回 False
                # 当前实现允许部分字段缺失
    
    return True
```

---

## Step 2.2: 在 _compress_chat_memory() 中集成 user_profile 更新

**Action:** 在 `_compress_chat_memory()` 函数的适当位置添加 user_profile 更新调用

**Note:** 这部分需要修改现有文件。请先在文件中找到 `_compress_chat_memory()` 函数，然后在适当位置插入代码。

**在文件中的定位：**

找到 `_compress_chat_memory()` 函数，在以下代码之后添加更新逻辑：

```python
# 4. 新增：检查并压缩（如需要）
await _compress_memory_bank_if_needed(user_id, llm_id)
```

**添加的新代码：**

```python
    # 5. 新增：更新 user_profile
    await _update_user_profile_in_compress(user_id, llm_id, recent_msg_list)


async def _update_user_profile_in_compress(
    user_id: str, 
    llm_id: str, 
    recent_msg_list: List[str]
) -> None:
    """
    在消息压缩时更新 user_profile
    
    这是 _compress_chat_memory 的辅助函数，负责协调 user_profile 的更新流程。
    
    Args:
        user_id: 用户ID
        llm_id: LLM ID
        recent_msg_list: 最近对话历史列表
    """
    # 检查输入有效性
    if not recent_msg_list:
        logger.debug(f"最近消息列表为空，跳过 user_profile 更新: user_id={user_id}")
        return
    
    try:
        # 获取当前 user_profile
        current_profile = await _get_user_profile(user_id, llm_id)
        
        if not current_profile:
            logger.info(f"当前 user_profile 不存在，无法更新: user_id={user_id}")
            return
        
        logger.debug(f"开始更新 user_profile: user_id={user_id}, 消息数={len(recent_msg_list)}")
        
        # 执行更新
        updated_profile = await _update_user_profile(current_profile, recent_msg_list)
        
        if updated_profile:
            # 检查是否真正有变化
            if updated_profile == current_profile:
                logger.debug(f"user_profile 无变化，无需保存: user_id={user_id}")
            else:
                # 保存更新后的 profile
                success = await _save_user_profile(updated_profile, user_id, llm_id)
                if success:
                    logger.info(f"user_profile 更新成功: user_id={user_id}")
                else:
                    logger.error(f"user_profile 保存失败: user_id={user_id}")
        else:
            logger.warning(f"user_profile 更新返回 None，保留原数据: user_id={user_id}")
            
    except Exception as e:
        logger.error(f"user_profile 更新过程中发生错误: {e}, user_id={user_id}", exc_info=True)
        # 发生错误时不应影响压缩流程的继续执行
```

---

## Step 2.3: 提交 Task 2 的更改

**Action:** 提交第二步的更改

```bash
git add app/service/chat_msg_service.py
git commit -m "feat: add user_profile update functions and integrate into compress flow

- Add _get_user_profile() to fetch current profile from Redis
- Add _save_user_profile() to save updated profile to Redis
- Add _build_profile_updater_chain() to build LLM chain
- Add _update_user_profile() to execute profile update with validation
- Add _validate_profile_structure() to verify 7-dimension integrity
- Add _update_user_profile_in_compress() to coordinate update in compress flow
- Integrate user_profile update into _compress_chat_memory()"
```

---

## Task 3: 添加必要的导入

**Files:**
- Modify: `app/service/chat_msg_service.py` (在文件顶部添加导入)

### Step 3.1: 添加导入语句

**Action:** 在 `chat_msg_service.py` 文件顶部添加必要的导入

**Note:** 这部分需要修改文件顶部。请确保不要删除现有的导入。

**添加的导入（如果尚未存在）：**

```python
# 确保以下导入已存在
import json
from typing import Optional, Dict, List

# 如果尚未导入，添加以下导入
# （请检查文件顶部是否已有这些导入）
```

**注意**：实际上，你可能需要检查 `chat_msg_service.py` 文件顶部是否已经有这些导入。通常这个文件会已经有 `json`、`Optional`、`Dict`、`List` 等导入。

### Step 3.2: 提交更改

**Action:** 提交导入更改（如果需要的话）

```bash
git add app/service/chat_msg_service.py
git commit -m "chore: add necessary imports for user_profile update" || echo "No changes to commit"
```

---

## Task 4: 测试

**Goal:** 验证 user_profile 动态更新功能正常工作

### Step 4.1: 创建测试脚本

**Action:** 创建测试脚本来验证功能

**Create:** `test_user_profile_update.py`

```python
#!/usr/bin/env python3
"""
测试 user_profile 动态更新功能
"""

import json
import asyncio
import sys
sys.path.insert(0, '.')

from app.service.chat_msg_service import (
    _get_user_profile,
    _save_user_profile,
    _validate_profile_structure,
    _update_user_profile
)


async def test_validate_profile_structure():
    """测试结构验证函数"""
    print("\n=== 测试 _validate_profile_structure ===")
    
    # 完整的 profile
    complete_profile = {
        "核心身份": {"姓名": "", "年龄": "", "职业": "", "与AI关系": ""},
        "核心性格": {"主导性格": "", "矛盾侧面": "", "小缺点": ""},
        "语言风格": {"口头禅": "", "语气词": "", "句式习惯": ""},
        "互动模式": {"开启话题": "", "安慰方式": "", "开玩笑": ""},
        "价值观": {"人生态度": "", "底线": "", "讨厌事物": ""},
        "长期兴趣": {"爱好": "", "喜欢": "", "讨厌": ""},
        "绝对边界": {"绝不说": [], "绝不做": []}
    }
    
    result = _validate_profile_structure(complete_profile)
    print(f"完整 profile 验证结果: {result}")
    assert result == True, "完整 profile 应该通过验证"
    
    # 缺少维度的 profile
    incomplete_profile = {
        "核心身份": {"姓名": "", "年龄": "", "职业": "", "与AI关系": ""},
        "核心性格": {"主导性格": "", "矛盾侧面": "", "小缺点": ""},
        # 缺少其他维度
    }
    
    result = _validate_profile_structure(incomplete_profile)
    print(f"不完整 profile 验证结果: {result}")
    assert result == False, "不完整的 profile 应该验证失败"
    
    print("✅ _validate_profile_structure 测试通过!")


async def test_structure_validation_only():
    """仅测试结构验证，不涉及 Redis 或 LLM"""
    print("\n" + "="*60)
    print("开始测试 user_profile 结构验证")
    print("="*60)
    
    await test_validate_profile_structure()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_structure_validation_only())
```

### Step 4.2: 运行测试

**Action:** 运行测试脚本

```bash
python test_user_profile_update.py
```

**Expected Output:**
```
============================================================
开始测试 user_profile 结构验证
============================================================

=== 测试 _validate_profile_structure ===
完整 profile 验证结果: True
不完整 profile 验证结果: False
✅ _validate_profile_structure 测试通过!

============================================================
测试完成！
============================================================
```

### Step 4.3: 提交测试文件

**Action:** 提交测试文件（可选）

```bash
# 测试文件可以不提交到仓库，但如果想保留的话：
# git add test_user_profile_update.py
# git commit -m "test: add test for user_profile update structure validation"
```

---

## Task 5: 最终集成测试

**Goal:** 完整测试 user_profile 更新流程

### Step 5.1: 验证代码集成

**Action:** 检查代码是否正确集成到 `_compress_chat_memory()`

**Verify:**

1. 打开 `app/service/chat_msg_service.py`
2. 找到 `_compress_chat_memory()` 函数
3. 确认在 `_compress_memory_bank_if_needed()` 之后调用了 `_update_user_profile_in_compress()`

**Expected Code:**

```python
async def _compress_chat_memory(user_id: str, llm_id: str):
    # ... 之前的代码 ...
    
    # 4. 新增：检查并压缩（如需要）
    await _compress_memory_bank_if_needed(user_id, llm_id)
    
    # 5. 新增：更新 user_profile
    await _update_user_profile_in_compress(user_id, llm_id, recent_msg_list)
```

### Step 5.2: 运行完整应用测试

**Action:** 如果可能，运行应用的测试套件

```bash
# 如果有 pytest 测试
pytest tests/ -v -k "memory or profile"

# 或者运行应用看看是否有语法错误
python -c "from app.service.chat_msg_service import _compress_chat_memory; print('Import successful')"
```

### Step 5.3: 最终提交

**Action:** 提交所有更改

```bash
# 检查更改
git status

# 添加所有更改
git add app/service/chat_msg_service.py
git add app/core/prompts/user_profile_updater.md

# 最终提交
git commit -m "feat: implement user_profile dynamic update

This commit adds the ability to dynamically update user_profile based on
conversation history during memory compression.

Features:
- Add user_profile_updater.md prompt template with strict update rules
- Add helper functions for fetching, updating, and saving user_profile
- Integrate user_profile update into _compress_chat_memory() workflow
- Implement strict validation to ensure 7-dimension structure integrity
- Distinguish between stable personality traits and temporary emotions

Technical Details:
- Update triggered every 30 messages during memory compression
- Uses json_ds_model for reliable JSON output
- Fails silently on errors, preserving original data
- Validates all 7 dimensions are present before saving

Related: PLAN_user_profile_update.md"
```

---

## Summary

这个实现计划包含以下任务：

### Task 1: 创建 Prompt 模板 ✅
- 创建 `app/core/prompts/user_profile_updater.md`
- 包含严格的更新规则和示例
- 区分稳定性格和临时情绪

### Task 2: 添加辅助函数 ✅
- `_get_user_profile()` - 获取当前 profile
- `_save_user_profile()` - 保存更新后的 profile
- `_build_profile_updater_chain()` - 构建 LLM chain
- `_update_user_profile()` - 执行更新逻辑
- `_validate_profile_structure()` - 验证结构完整性
- `_update_user_profile_in_compress()` - 协调更新流程

### Task 3: 添加导入 ✅
- 确保所有必要的导入都已存在

### Task 4: 测试 ✅
- 创建测试脚本
- 验证结构验证函数

### Task 5: 最终集成测试 ✅
- 验证代码集成
- 运行完整测试
- 提交最终更改

---

**下一步：** 使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 来执行这个计划。

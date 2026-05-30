package com.bedfox.service.service.impl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.pojo.vo.LlmMemoryVo;
import com.bedfox.service.service.LlmMemoryService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * 模型记忆面板 Service 实现
 * 纯 Redis 读取，不改数据库
 * @author bedFox
 */
@Slf4j
@Service
public class LlmMemoryServiceImpl implements LlmMemoryService {

    private static final String MEMORY_KEY_PREFIX = "chat:memory:";

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    @Override
    public LlmMemoryVo getMemory(String llmId) {
        String userId = LoginUserHolder.getUserId();
        String baseKey = MEMORY_KEY_PREFIX + userId + ":" + llmId + ":";

        LlmMemoryVo vo = new LlmMemoryVo();

        // 1. 角色卡
        String characterCardJson = redisTemplate.opsForValue().get(baseKey + "character_card");
        if (characterCardJson != null) {
            try {
                JSONObject card = JSON.parseObject(characterCardJson);
                vo.setCharacterName(card.getString("名字"));
                vo.setCharacterPersonality(card.getString("性格关键词"));
                vo.setCharacterDescription(card.getString("核心描述"));
                vo.setCharacterActionStyle(card.getString("动作风格"));
                if (card.get("常用动作") != null) {
                    vo.setCharacterCommonActions(card.getList("常用动作", String.class));
                }
                vo.setTalkativeness(card.getDouble("健谈程度"));
                vo.setCharacterExamples(card.getString("示例对话"));
            } catch (Exception e) {
                log.warn("解析角色卡 JSON 失败: {}", e.getMessage());
            }
        }

        // 2. 核心锚点
        String coreAnchor = redisTemplate.opsForValue().get(baseKey + "core_anchor");
        if (coreAnchor != null) {
            parseCoreAnchor(coreAnchor, vo);
        }

        // 3. 用户画像
        String userProfileJson = redisTemplate.opsForValue().get(baseKey + "user_profile");
        if (userProfileJson != null) {
            try {
                JSONObject profile = JSON.parseObject(userProfileJson);
                List<String> parts = new ArrayList<>();
                for (String key : profile.keySet()) {
                    Object val = profile.get(key);
                    if (val instanceof JSONObject) {
                        JSONObject dim = (JSONObject) val;
                        List<String> items = new ArrayList<>();
                        for (String dk : dim.keySet()) {
                            Object dv = dim.get(dk);
                            if (dv != null && !"[未提及]".equals(String.valueOf(dv))) {
                                items.add(dk + "：" + dv);
                            }
                        }
                        if (!items.isEmpty()) {
                            parts.add(key + "：" + String.join("、", items));
                        }
                    } else if (val != null && !"[未提及]".equals(String.valueOf(val))) {
                        parts.add(key + "：" + val);
                    }
                }
                vo.setUserProfile(String.join("\n", parts));
            } catch (Exception e) {
                vo.setUserProfile(userProfileJson);
            }
        }

        // 4. 记忆银行
        String memoryBankJson = redisTemplate.opsForValue().get(baseKey + "memory_bank");
        if (memoryBankJson != null) {
            try {
                JSONArray bank = JSON.parseArray(memoryBankJson);
                List<LlmMemoryVo.MemoryEventItem> events = new ArrayList<>();
                int total = bank.size();
                int start = Math.max(0, total - 20); // 最近20条
                for (int i = start; i < total; i++) {
                    JSONObject item = bank.getJSONObject(i);
                    LlmMemoryVo.MemoryEventItem eventItem = new LlmMemoryVo.MemoryEventItem();
                    eventItem.setEventId(item.getString("event_id"));
                    eventItem.setOccurredAt(item.getString("occurred_at"));
                    eventItem.setActor(item.getString("actor"));
                    eventItem.setCategory(item.getString("category"));
                    eventItem.setEventType(item.getString("event_type"));
                    eventItem.setContent(item.getString("content"));
                    if (item.get("keywords") != null) {
                        eventItem.setKeywords(item.getList("keywords", String.class));
                    }
                    eventItem.setImportance(item.getDouble("importance"));
                    eventItem.setSourceSnippet(item.getString("source_snippet"));
                    events.add(eventItem);
                }
                vo.setMemoryEvents(events);
            } catch (Exception e) {
                log.warn("解析记忆银行 JSON 失败: {}", e.getMessage());
            }
        }

        // 5. 当前情绪
        vo.setCurrentEmotion(redisTemplate.opsForValue().get(baseKey + "role_emotion_state"));

        return vo;
    }

    /**
     * 解析核心锚点文本
     */
    private void parseCoreAnchor(String text, LlmMemoryVo vo) {
        // 提取【角色声明】
        int declStart = text.indexOf("【角色声明】");
        int anchorStart = text.indexOf("【角色核心锚点】");
        int boundaryStart = text.indexOf("【绝对边界】");

        if (declStart >= 0) {
            int declEnd = anchorStart > declStart ? anchorStart : (boundaryStart > declStart ? boundaryStart : text.length());
            vo.setRoleDeclaration(text.substring(declStart + 6, declEnd).trim());
        }

        if (anchorStart >= 0) {
            int anchorEnd = boundaryStart > anchorStart ? boundaryStart : text.length();
            vo.setCoreAnchorText(text.substring(anchorStart + 8, anchorEnd).trim());
        } else if (declStart < 0 && boundaryStart < 0) {
            // 纯文本，没有标记
            vo.setCoreAnchorText(text.trim());
        }
    }
}

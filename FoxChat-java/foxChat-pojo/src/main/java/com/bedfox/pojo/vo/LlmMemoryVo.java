package com.bedfox.pojo.vo;

import lombok.Data;

import java.util.List;

/**
 * 模型记忆面板 VO
 * @author bedFox
 */
@Data
public class LlmMemoryVo {

    /** 角色卡：名字 */
    private String characterName;
    /** 角色卡：性格关键词 */
    private String characterPersonality;
    /** 角色卡：核心描述 */
    private String characterDescription;
    /** 角色卡：动作风格 */
    private String characterActionStyle;
    /** 角色卡：常用动作 */
    private List<String> characterCommonActions;
    /** 角色卡：健谈程度 0.0-1.0 */
    private Double talkativeness;
    /** 角色卡：示例对话 */
    private String characterExamples;

    /** 核心锚点：角色声明 */
    private String roleDeclaration;
    /** 核心锚点：核心锚点文本 */
    private String coreAnchorText;

    /** 用户画像文本 */
    private String userProfile;

    /** 记忆银行事件列表 */
    private List<MemoryEventItem> memoryEvents;

    /** 当前情绪 */
    private String currentEmotion;

    @Data
    public static class MemoryEventItem {
        private String eventId;
        private String occurredAt;
        private String actor;
        private String category;
        private String eventType;
        private String content;
        private List<String> keywords;
        private Double importance;
        private String sourceSnippet;
    }
}

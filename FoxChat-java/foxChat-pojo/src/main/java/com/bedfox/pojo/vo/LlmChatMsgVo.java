package com.bedfox.pojo.vo;

import lombok.Data;

/**
 * LLM 聊天消息响应 VO
 * @author bedFox
 * @date 2026/3/21 20:12
 */
@Data
public class LlmChatMsgVo {
    /**
     * 消息内容（JSON 格式，包含 blocks 和 emotion）
     * 前端会自动解析此 JSON 字符串
     */
    private String msg;
}

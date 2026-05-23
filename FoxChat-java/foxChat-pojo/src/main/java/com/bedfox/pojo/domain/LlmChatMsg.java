package com.bedfox.pojo.domain;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 
 * @TableName llm_chat_msg
 */
@TableName(value ="llm_chat_msg")
@Data
public class LlmChatMsg implements Serializable {
    /**
     * id
     */
    @TableId
    private String id;

    /**
     * 发送者id
     */
    private String sendUserId;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 消息状态(0发送/1存入db/2存入rag)
     */
    private Integer status;

    /**
     * 消息内容
     */
    private String msgContent;

    /**
     * 模型id
     */
    private String llmId;

    /**
     * 是否是ai消息
     */
    private Boolean isHuman;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}
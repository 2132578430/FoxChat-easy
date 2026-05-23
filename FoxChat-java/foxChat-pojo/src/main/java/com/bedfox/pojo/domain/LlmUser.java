package com.bedfox.pojo.domain;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;

/**
 * 
 * @TableName llm_user
 */
@TableName(value ="llm_user")
@Data
public class LlmUser implements Serializable {
    /**
     * ID
     */
    @TableId
    private String id;

    /**
     * 用户ID
     */
    private String userId;

    /**
     * 模型昵称
     */
    private String llmName;

    /**
     * 模型头像
     */
    private String faceImage;

    /**
     * 初始化记忆
     */
    private String memoryContent;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}
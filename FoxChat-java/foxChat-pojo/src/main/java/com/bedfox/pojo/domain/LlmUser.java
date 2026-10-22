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

    /**
     * 初始化状态（0未初始化/1初始化中/2就绪/3初始化失败）
     */
    @TableField("isApply")
    private Integer isApply;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}
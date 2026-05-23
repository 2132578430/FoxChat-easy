package com.bedfox.pojo.vo;

import com.baomidou.mybatisplus.annotation.TableId;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author bedFox
 * @date 2026/3/25 09:49
 */
@Data
public class LlmMsgHistoryVo {
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
}

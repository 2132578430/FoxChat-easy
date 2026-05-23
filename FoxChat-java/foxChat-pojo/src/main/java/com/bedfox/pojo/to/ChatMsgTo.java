package com.bedfox.pojo.to;

import lombok.Data;

/**
 * @author bedFox
 * @date 2026/3/22 21:05
 */
@Data
public class ChatMsgTo {
    String userId;
    String msgContent;
    String llmId;
}

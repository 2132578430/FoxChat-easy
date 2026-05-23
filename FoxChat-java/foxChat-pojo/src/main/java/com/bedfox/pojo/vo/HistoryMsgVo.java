package com.bedfox.pojo.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author bedFox
 */
@Data
public class HistoryMsgVo {
    String msgId;
    String msg;
    LocalDateTime tempTime;
    String createTime;
    String sendUserId;
    Boolean status;
}

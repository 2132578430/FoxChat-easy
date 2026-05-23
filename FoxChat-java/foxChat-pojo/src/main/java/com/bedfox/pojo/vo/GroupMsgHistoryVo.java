package com.bedfox.pojo.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author bedFox
 */
@Data
public class GroupMsgHistoryVo {

    private String id;
    private String groupId;
    private String msgContent;
    /**
     * 1文本2图片3视频
     */
    private Integer msgType;
    private LocalDateTime tempTime;
    private String createTime;

    // 发送人信息
    private String sendUserId;
    private String username;
    private String faceImage;
    private String nickname;
}

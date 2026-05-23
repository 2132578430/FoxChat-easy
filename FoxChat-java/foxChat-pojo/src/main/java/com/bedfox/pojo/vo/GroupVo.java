package com.bedfox.pojo.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author bedFox
 */
@Data
public class GroupVo {
    /**
     * 群聊id
     */
    private String id;

    /**
     * 群聊名称
     */
    private String groupName;

    /**
     * 群主userId
     */
    private String ownerUserId;

    /**
     * 群聊头像
     */
    private String faceImage;

    /**
     *
     */
    private LocalDateTime createTime;

    /**
     *
     */
    private Integer role;

    /**
     * 是否已加入
     */
    private Boolean isJoined;
}

package com.bedfox.pojo.vo;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class FriendVo {
    String userId;
    String username;
    String nickname;
    String faceImage;
    Boolean online;
    Integer role;

    /**
     * 初始化状态（0未初始化/1初始化中/2就绪/3初始化失败）
     */
    Integer isApply;
}

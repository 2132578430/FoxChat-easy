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
     * 是否启用（0禁止/1转化记忆中/2启用）
     */
    Integer isApply;
}

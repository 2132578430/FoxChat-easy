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
}

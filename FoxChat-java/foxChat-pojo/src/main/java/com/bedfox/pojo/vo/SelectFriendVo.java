package com.bedfox.pojo.vo;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class SelectFriendVo {
    String userId;
    String nickname;
    String faceImage;
    String username;
    Boolean online;
}

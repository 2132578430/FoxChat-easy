package com.bedfox.pojo.vo;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class SearchUserVo {
    String userId;
    String username;
    String nickname;
    String faceImage;
    Boolean isFriend;
}

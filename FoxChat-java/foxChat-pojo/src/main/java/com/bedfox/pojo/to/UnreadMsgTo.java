package com.bedfox.pojo.to;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class UnreadMsgTo {
    Long count;
    String friendUserId;
}

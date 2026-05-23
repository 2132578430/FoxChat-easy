package com.bedfox.pojo.dto;

import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.GroupMsg;
import com.bedfox.pojo.domain.Users;
import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class MsgDto {
    private Integer type;
    private ChatMsg chatMsg;
    private String extend;
    private Integer targetType;
    private GroupMsg groupMsg;
    private Users sender;
}

package com.bedfox.common.constant;

import lombok.Getter;

/**
 * @author bedFox
 * 11 - netty信息服务
 *  00 - 连接
 *  01 - 发送信息
 *  02 - 签收信息
 *  03 - 心跳检测
 *  04 - 申请好友
 *  05 - 拉取好友
 *  06 - 好友上线
 *  07 - 用户离线
 * 12 - netty群聊服务
 *  01 - 群聊信息发送
 */
@Getter
public enum MsgTypeConstant {
    // 私人信息
    CONNECT(1100, "连接webSocket服务器"),
    CHAT(1101, "发送信息"),
    SIGNED(1102, "签收信息"),
    HEART(1103, "心跳检测"),
    REQUEST_FRIEND(1104, "申请好友"),
    PULL_FRIEND(1105, "拉取好友"),
    FRIEND_ONLINE(1106,"好友上线"),
    USER_LOGOUT(1107, "用户离线"),

    // 群聊信息
    GROUP_CHAT(1201, "群聊信息发送");

    private final Integer code;
    private final String msg;

    MsgTypeConstant(Integer code, String msg) {
        this.code = code;
        this.msg = msg;
    }

}

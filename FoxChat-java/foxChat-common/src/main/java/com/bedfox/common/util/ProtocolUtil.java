package com.bedfox.common.util;

import com.bedfox.common.constant.MsgTargetTypeConstant;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.pojo.domain.GroupMsg;
import com.bedfox.pojo.dto.MsgDto;
import org.apache.commons.lang3.StringUtils;

import java.time.LocalDateTime;
import java.util.Base64;

/**
 * @author bedFox
 */
public class ProtocolUtil {
    /**
     * 将msgDto对象转化为protocol对象
     * @param msgDto
     * @return
     */
    public static ChatProtocol.Message msgDtoToProtocol(MsgDto msgDto) {
        ChatProtocol.Message.Builder msgBuilder = ChatProtocol.Message.newBuilder();
        msgBuilder.setType(safeIntegerValue(msgDto.getType()));
        msgBuilder.setExtend(safeStringValue(msgDto.getExtend()));
        msgBuilder.setTargetType(safeIntegerValue(msgDto.getTargetType()));

        // 检查传入的信息类型
        if (msgDto.getChatMsg() != null) {
            msgBuilder.setChatMsg(buildChatMsg(msgDto));
        } else if (msgDto.getGroupMsg() != null) {
            msgBuilder.setGroupMsg(buildGroupMsg(msgDto));
        }

        return msgBuilder.build();
    }

    /**
     * 构建ChatMsg
     * @param msgDto
     * @return
     */
    private static ChatProtocol.ChatMsg buildChatMsg(MsgDto msgDto) {
        ChatMsg chatMsg = msgDto.getChatMsg();
        ChatProtocol.ChatMsg.Builder chatMsgProtocol = ChatProtocol.ChatMsg.newBuilder();

        chatMsgProtocol.setMsg(safeStringValue(chatMsg.getMsg()));
        chatMsgProtocol.setId(safeStringValue(chatMsg.getId()));
        chatMsgProtocol.setSignFlag(safeBooleanValue(chatMsg.getSignFlag()));
        chatMsgProtocol.setAcceptUserId(safeStringValue(chatMsg.getAcceptUserId()));

        chatMsgProtocol.setSender(buildUserDef(chatMsg.getSendUserId(), msgDto));

        if (chatMsg.getCreateTime() != null) {
            chatMsgProtocol.setCreateTime(TimeUtil.ldtToTimestamp(chatMsg.getCreateTime()).toString());
        } else {
            chatMsgProtocol.setCreateTime(String.valueOf(System.currentTimeMillis()));
        }
        return chatMsgProtocol.build();
    }

    /**
     * 构建GroupMsg
     * @param msgDto
     * @return
     */
    private static ChatProtocol.GroupMsg buildGroupMsg(MsgDto msgDto) {
        GroupMsg groupMsg = msgDto.getGroupMsg();
        ChatProtocol.GroupMsg.Builder groupMsgProtocol = ChatProtocol.GroupMsg.newBuilder();

        groupMsgProtocol.setId(safeStringValue(groupMsg.getId()));
        groupMsgProtocol.setGroupId(safeStringValue(groupMsg.getGroupId()));
        groupMsgProtocol.setMsg(safeStringValue(groupMsg.getMsgContent()));
        groupMsgProtocol.setMsgType(safeStringValue(String.valueOf(groupMsg.getMsgType())));

        if (groupMsg.getCreateTime() != null) {
            groupMsgProtocol.setCreateTime(TimeUtil.ldtToTimestamp(groupMsg.getCreateTime()).toString());
        } else {
            groupMsgProtocol.setCreateTime(String.valueOf(System.currentTimeMillis()));
        }

        groupMsgProtocol.setSender(buildUserDef(groupMsg.getSendUserId(), msgDto));
        return groupMsgProtocol.build();
    }

    /**
     * 构建发送者信息
     * @param sendUserId
     * @param msgDto
     * @return
     */
    private static ChatProtocol.UserDef.Builder buildUserDef(String sendUserId, MsgDto msgDto) {
        ChatProtocol.UserDef.Builder userDefBuilder = ChatProtocol.UserDef.newBuilder();
        userDefBuilder.setUserId(safeStringValue(sendUserId));

        if (msgDto.getSender() != null) {
            userDefBuilder.setUsername(safeStringValue(msgDto.getSender().getUsername()));
            userDefBuilder.setNickname(safeStringValue(msgDto.getSender().getNickname()));
            userDefBuilder.setFaceImage(safeStringValue(msgDto.getSender().getFaceImage()));
        }
        return userDefBuilder;
    }

    private static int safeIntegerValue(Integer type) {
        return type == null ? 0 : type;
    }

    private static String safeStringValue(String value) {
        return StringUtils.isEmpty(value) ? "" : value;
    }

    private static boolean safeBooleanValue(Boolean value) {
        return value != null && value;
    }

    public static MsgDto protocolToMsgDto(ChatProtocol.Message msgProtocol) {
        MsgDto msgDto = new MsgDto();

        msgDto.setType(msgProtocol.getType());
        msgDto.setExtend(msgProtocol.getExtend());
        msgDto.setTargetType(msgProtocol.getTargetType());

        if (MsgTargetTypeConstant.GROUP_CHAT.equals(msgProtocol.getTargetType())) {
            buildGroupMsg(msgProtocol, msgDto);
        } else {
            buildChatMsg(msgProtocol, msgDto);
        }
        return msgDto;
    }

    private static void buildGroupMsg(ChatProtocol.Message msgProtocol, MsgDto msgDto) {
        GroupMsg groupMsg = new GroupMsg();
        ChatProtocol.GroupMsg msg = msgProtocol.getGroupMsg();

        groupMsg.setId(msg.getId());
        groupMsg.setMsgContent(msg.getMsg());
        groupMsg.setMsgType(Integer.valueOf(msg.getMsgType()));
        groupMsg.setSendUserId(msg.getSender().getUserId());
        groupMsg.setGroupId(msg.getGroupId());
        if (!StringUtils.isEmpty(msg.getCreateTime())) {
            groupMsg.setCreateTime(TimeUtil.timestampToLdt(Long.valueOf(msg.getCreateTime())));
        } else {
            groupMsg.setCreateTime(LocalDateTime.now());
        }

        msgDto.setGroupMsg(groupMsg);
    }

    private static void buildChatMsg(ChatProtocol.Message msgProtocol, MsgDto msgDto) {
        ChatMsg chatMsg = new ChatMsg();
        ChatProtocol.ChatMsg msg = msgProtocol.getChatMsg();

        chatMsg.setMsg(msg.getMsg());
        chatMsg.setId(msg.getId());
        chatMsg.setSignFlag(msg.getSignFlag());
        chatMsg.setAcceptUserId(msg.getAcceptUserId());
        chatMsg.setSendUserId(msg.getSender().getUserId());
        if (!StringUtils.isEmpty(msg.getCreateTime())) {
            chatMsg.setCreateTime(TimeUtil.timestampToLdt(Long.parseLong(msg.getCreateTime())));
        } else {
            chatMsg.setCreateTime(LocalDateTime.now());
        }

        msgDto.setChatMsg(chatMsg);
    }

    public static String toProtocolBase64(MsgDto msgDto) {
        byte[] byteArray = msgDtoToProtocol(msgDto).toByteArray();
        return Base64.getEncoder().encodeToString(byteArray);
    }

    public static String protocolToBase64(ChatProtocol.Message message) {
        return Base64.getEncoder().encodeToString(message.toByteArray());
    }

}

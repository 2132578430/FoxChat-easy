package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.dto.HistoryUserDto;
import com.bedfox.pojo.dto.WithdrawMsgDto;
import com.bedfox.service.mapper.ChatMsgMapper;
import com.bedfox.service.service.ChatMsgService;
import com.bedfox.service.service.MsgStatusService;
import com.bedfox.pojo.to.UnreadMsgTo;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.TimeUtil;
import com.bedfox.pojo.vo.HistoryMsgVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
* @author 21325
* @description 针对表【chat_msg】的数据库操作Service实现
* @createDate 2026-02-12 00:49:01
*/
@Slf4j
@Service
public class ChatMsgServiceImpl extends ServiceImpl<ChatMsgMapper, ChatMsg>
    implements ChatMsgService{

    @Resource
    ChatMsgMapper chatMsgMapper;

    @Resource
    MsgStatusService msgStatusService;

    /**
     * 保存信息对象并返回信息Id
     * @param chatMsg
     * @return
     */
    @Override
    public String saveMsg(ChatMsg chatMsg) {
        ChatMsg msg = new ChatMsg();

        msg.setId(chatMsg.getId());
        msg.setMsg(chatMsg.getMsg());
        msg.setSendUserId(chatMsg.getSendUserId());
        msg.setAcceptUserId(chatMsg.getAcceptUserId());
        msg.setSignFlag(false);
        msg.setCreateTime(LocalDateTime.now());

        save(msg);
        // 保存消息状态
        msgStatusService.saveMsgStatus(msg);

        return msg.getId();
    }

    /**
     * 签收信息
     * @param msgIdList
     */
    @Transactional
    @Override
    public void signMsg(List<String> msgIdList) {
        List<ChatMsg> chatMsgList = msgIdList.stream()
                .map(msgId -> {
                    ChatMsg chatMsg = new ChatMsg();

                    chatMsg.setId(msgId);
                    chatMsg.setSignFlag(true);
                    return chatMsg;
                }).toList();

        updateBatchById(chatMsgList);
    }

    /**
     * 查询当前用户未读信息列表
     * @return
     */
    @Override
    public String noSignMsg(String friendId) {
        String userId = LoginUserHolder.getUserId();

        List<ChatMsg> msgList = list(new LambdaQueryWrapper<ChatMsg>()
                .eq(ChatMsg::getSignFlag, false)
                .eq(ChatMsg::getAcceptUserId, userId)
                .eq(ChatMsg::getSendUserId, friendId));

        List<String> msgIdList = msgList.stream().map(ChatMsg::getId).toList();

        return msgIdList.isEmpty() ? "" : String.join(",", msgIdList);
    }

    /**
     * 按照时间戳分页查询信息
     * @param historyUserDto
     * @return
     */
    @Override
    public List<HistoryMsgVo> msgHistory(HistoryUserDto historyUserDto) {
        String userId = LoginUserHolder.getUserId();
        String friendId = historyUserDto.getFriendId();
        Long lastTimestamp = historyUserDto.getLastTimestamp();

        LocalDateTime dateTime = TimeUtil.timestampToLdt(lastTimestamp);

        List<HistoryMsgVo> historyMsgList = chatMsgMapper.msgPageByTime(userId, friendId, dateTime);

        return historyMsgList.stream()
                .peek(historyMsgVo ->
                            historyMsgVo.setCreateTime(TimeUtil.ldtToTimestamp(historyMsgVo.getTempTime()).toString()))
                .toList();
    }

    /**
     * 获取所有好友相关得未读信息
     *
     * @return
     */
    @Override
    public Map<String, Long> getUnreadCount() {
        String userId = LoginUserHolder.getUserId();

        List<UnreadMsgTo> msgList = chatMsgMapper.getUnreadCount(userId);

        return msgList.stream()
                .collect(Collectors
                        .toMap(UnreadMsgTo::getFriendUserId, UnreadMsgTo::getCount));
    }

    /**
     * 撤回信息
     * @param withdrawMsgDto
     */
    @Transactional
    @Override
    public void withdrawMsg(WithdrawMsgDto withdrawMsgDto) {
        List<String> msgIds = withdrawMsgDto.getMsgIds();

        removeBatchByIds(msgIds);
    }
}





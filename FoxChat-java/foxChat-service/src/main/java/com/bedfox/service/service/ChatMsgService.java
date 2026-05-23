package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.dto.HistoryUserDto;
import com.bedfox.pojo.dto.WithdrawMsgDto;
import com.bedfox.pojo.vo.HistoryMsgVo;

import java.util.List;
import java.util.Map;

/**
* @author 21325
* @description 针对表【chat_msg】的数据库操作Service
* @createDate 2026-02-12 00:49:01
*/
public interface ChatMsgService extends IService<ChatMsg> {

    String saveMsg(ChatMsg chatMsg);

    void signMsg(List<String> msgIdList);

    String noSignMsg(String friendId);

    List<HistoryMsgVo> msgHistory(HistoryUserDto historyUserDto);

    Map<String, Long> getUnreadCount();

    void withdrawMsg(WithdrawMsgDto withdrawMsgDto);

}

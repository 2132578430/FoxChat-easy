package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.to.UnreadMsgTo;
import com.bedfox.pojo.vo.HistoryMsgVo;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【chat_msg】的数据库操作Mapper
* @createDate 2026-02-12 00:49:01
* @Entity com.bedfox.bedfoxchat.domain.ChatMsg
*/
public interface ChatMsgMapper extends BaseMapper<ChatMsg> {

    List<HistoryMsgVo> msgPageByTime(@Param("userId") String userId, @Param("friendId") String friendId, @Param("dateTime") LocalDateTime dateTime);

    List<UnreadMsgTo> getUnreadCount(@Param("userId") String userId);
}





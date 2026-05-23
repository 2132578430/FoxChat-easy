package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.LlmChatMsg;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【llm_chat_msg】的数据库操作Mapper
* @createDate 2026-03-25 09:46:16
* @Entity com.bedfox.bedfoxchat.domain.LlmChatMsg
*/
public interface LlmChatMsgMapper extends BaseMapper<LlmChatMsg> {

    List<LlmChatMsg> getMsgHistory(@Param("userId") String userId, @Param("llmId") String llmId, @Param("lastTime") LocalDateTime lastTime, @Param("lastId") String lastId);
}





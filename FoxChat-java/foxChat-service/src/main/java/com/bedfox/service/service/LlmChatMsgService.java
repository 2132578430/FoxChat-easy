package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.vo.LlmMsgHistoryVo;

import java.util.List;

/**
* @author 21325
* @description 针对表【llm_chat_msg】的数据库操作Service
* @createDate 2026-03-25 09:46:16
*/
public interface LlmChatMsgService extends IService<LlmChatMsg> {

    List<LlmMsgHistoryVo> getMsgHistory(String userId, String llmId, Long lastTime, String lastId);
}

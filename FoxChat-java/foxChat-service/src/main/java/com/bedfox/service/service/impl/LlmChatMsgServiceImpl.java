package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.common.util.TimeUtil;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.vo.LlmMsgHistoryVo;
import com.bedfox.service.mapper.LlmChatMsgMapper;
import com.bedfox.service.service.LlmChatMsgService;
import jakarta.annotation.Resource;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【llm_chat_msg】的数据库操作Service实现
* @createDate 2026-03-25 09:46:16
*/
@Service
public class LlmChatMsgServiceImpl extends ServiceImpl<LlmChatMsgMapper, LlmChatMsg>
    implements LlmChatMsgService{

    @Resource
    LlmChatMsgMapper llmChatMsgMapper;

    @Override
    public List<LlmMsgHistoryVo> getMsgHistory(String userId, String llmId, Long lastTime, String lastId) {
        LocalDateTime currentTime = TimeUtil.timestampToLdt(lastTime);

        List<LlmChatMsg> llmChatMsgList = llmChatMsgMapper.getMsgHistory(userId, llmId, currentTime, lastId);

        return llmChatMsgList.stream()
                .map(llmChatMsg -> {
                    LlmMsgHistoryVo chatMsgVo = new LlmMsgHistoryVo();
                    BeanUtils.copyProperties(llmChatMsg, chatMsgVo);
                    return chatMsgVo;
                })
                .toList();
    }
}





package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.MsgStatus;
import com.bedfox.pojo.dto.DeleteMsgDto;
import com.bedfox.service.mapper.MsgStatusMapper;
import com.bedfox.service.service.MsgStatusService;
import com.bedfox.common.util.LoginUserHolder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
* @author 21325
* @description 针对表【msg_status】的数据库操作Service实现
* @createDate 2026-02-21 07:10:38
*/
@Service
public class MsgStatusServiceImpl extends ServiceImpl<MsgStatusMapper, MsgStatus>
    implements MsgStatusService{

    @Autowired
    MsgStatusMapper msgStatusMapper;

    @Transactional
    @Override
    public void saveMsgStatus(ChatMsg msg) {
        MsgStatus msgStatus1 = new MsgStatus();
        MsgStatus msgStatus2 = new MsgStatus();

        msgStatus1.setStatus(1);
        msgStatus1.setUserId(msg.getAcceptUserId());
        msgStatus1.setMsgId(msg.getId());

        msgStatus2.setStatus(1);
        msgStatus2.setUserId(msg.getSendUserId());
        msgStatus2.setMsgId(msg.getId());

        saveBatch(List.of(msgStatus1, msgStatus2));
    }

    /**
     * 删除信息（修改信息删除状态）
     *
     * @param deleteMsgDto
     */
    @Transactional
    @Override
    public void deleteMsg(DeleteMsgDto deleteMsgDto) {
        String userId = LoginUserHolder.getUserId();

        List<String> msgIds = deleteMsgDto.getMsgIds();

        LambdaUpdateWrapper<MsgStatus> updateWrapper = new LambdaUpdateWrapper<>();

        updateWrapper.set(MsgStatus::getStatus, 0)
                        .eq(MsgStatus::getUserId, userId)
                                .in(MsgStatus::getMsgId, msgIds);

        update(updateWrapper);
    }
}





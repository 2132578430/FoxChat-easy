package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.ChatMsg;
import com.bedfox.pojo.domain.MsgStatus;
import com.bedfox.pojo.dto.DeleteMsgDto;

/**
* @author 21325
* @description 针对表【msg_status】的数据库操作Service
* @createDate 2026-02-21 07:10:38
*/
public interface MsgStatusService extends IService<MsgStatus> {

    void saveMsgStatus(ChatMsg msg);

    void deleteMsg(DeleteMsgDto deleteMsgDto);
}

package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.GroupMsg;
import com.bedfox.pojo.dto.HistoryGroupDto;
import com.bedfox.pojo.vo.GroupMsgHistoryVo;

import java.util.List;

/**
* @author 21325
* @description 针对表【group_msg】的数据库操作Service
* @createDate 2026-02-21 20:16:14
*/
public interface GroupMsgService extends IService<GroupMsg> {

    List<GroupMsgHistoryVo> historyMsg(HistoryGroupDto historyGroupDto);
}

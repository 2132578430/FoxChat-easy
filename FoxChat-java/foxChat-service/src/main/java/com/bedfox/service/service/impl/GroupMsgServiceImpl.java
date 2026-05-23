package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.GroupMsg;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.HistoryGroupDto;
import com.bedfox.service.mapper.GroupMsgMapper;
import com.bedfox.service.service.GroupMsgService;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.TimeUtil;
import com.bedfox.pojo.vo.GroupMsgHistoryVo;
import jakarta.annotation.Resource;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【group_msg】的数据库操作Service实现
* @createDate 2026-02-21 20:16:14
*/
@Service
public class GroupMsgServiceImpl extends ServiceImpl<GroupMsgMapper, GroupMsg>
    implements GroupMsgService{

    @Resource
    GroupMsgMapper groupMsgMapper;

    @Resource
    UsersService usersService;

    @Override
    public List<GroupMsgHistoryVo> historyMsg(HistoryGroupDto historyGroupDto) {
        String groupId = historyGroupDto.getGroupId();
        Long lastTimestamp = historyGroupDto.getLastTimestamp();
        LocalDateTime dateTime;

        if (lastTimestamp == null || lastTimestamp == 0) {
            dateTime = LocalDateTime.now();
        } else {
            dateTime = TimeUtil.timestampToLdt(lastTimestamp);
        }

        List<GroupMsg> groupMsgList = groupMsgMapper.historyMsg(groupId, dateTime);

        return groupMsgList.stream()
                .map(groupMsg -> {
                    GroupMsgHistoryVo historyVo = new GroupMsgHistoryVo();
                    Long createTime = TimeUtil.ldtToTimestamp(groupMsg.getCreateTime());
                    historyVo.setCreateTime(createTime.toString());

                    BeanUtils.copyProperties(groupMsg, historyVo);

                    Users users = usersService.getById(groupMsg.getSendUserId());

                    historyVo.setUsername(users.getUsername());
                    historyVo.setNickname(users.getNickname());
                    historyVo.setFaceImage(users.getFaceImage());

                    return historyVo;
                })
                .toList();
    }
}





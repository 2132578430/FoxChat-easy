package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.GroupMsg;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【group_msg】的数据库操作Mapper
* @createDate 2026-02-21 20:16:14
* @Entity com.bedfox.bedfoxchat.domain.GroupMsg
*/
public interface GroupMsgMapper extends BaseMapper<GroupMsg> {

    List<GroupMsg> historyMsg(@Param("groupId") String groupId, @Param("dateTime") LocalDateTime dateTime);
}





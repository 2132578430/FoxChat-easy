package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.GroupMember;
import com.bedfox.pojo.vo.GroupVo;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
* @author 21325
* @description 针对表【group_member】的数据库操作Mapper
* @createDate 2026-02-21 20:20:25
* @Entity com.bedfox.bedfoxchat.domain.GroupMember
*/
public interface GroupMemberMapper extends BaseMapper<GroupMember> {

    List<GroupVo> queryGroupByUserId(@Param("userId") String userId);
}





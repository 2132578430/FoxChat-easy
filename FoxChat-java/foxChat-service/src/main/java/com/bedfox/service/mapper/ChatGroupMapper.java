package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.ChatGroup;
import com.bedfox.pojo.vo.GroupVo;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
* @author 21325
* @description 针对表【chat_group】的数据库操作Mapper
* @createDate 2026-02-21 22:10:23
* @Entity com.bedfox.bedfoxchat.domain.ChatGroup
*/
public interface ChatGroupMapper extends BaseMapper<ChatGroup> {

    List<GroupVo> searchGroupWithStatus(@Param("keyword") String keyword, @Param("userId") String userId);
}





package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.ChatGroup;
import com.bedfox.pojo.dto.GroupDto;
import com.bedfox.pojo.vo.GroupVo;

import java.util.List;

/**
* @author 21325
* @description 针对表【chat_group】的数据库操作Service
* @createDate 2026-02-21 22:10:23
*/
public interface ChatGroupService extends IService<ChatGroup> {

    void addGroup(GroupDto groupDto);

    List<GroupVo> listGroup();

    void applyGroup(String groupId, String reason);

    List<GroupVo> searchGroup(String keyword);
}

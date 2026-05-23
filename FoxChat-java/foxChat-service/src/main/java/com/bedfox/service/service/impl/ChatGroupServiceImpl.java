package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.common.constant.GroupConstant;
import com.bedfox.pojo.domain.ChatGroup;
import com.bedfox.pojo.domain.GroupMember;
import com.bedfox.pojo.dto.GroupDto;
import com.bedfox.service.mapper.ChatGroupMapper;
import com.bedfox.service.mapper.GroupMemberMapper;
import com.bedfox.service.service.ChatGroupService;
import com.bedfox.service.service.GroupMemberService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.pojo.vo.GroupVo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/**
* @author 21325
* @description 针对表【chat_group】的数据库操作Service实现
* @createDate 2026-02-21 22:10:23
*/
@Service
public class ChatGroupServiceImpl extends ServiceImpl<ChatGroupMapper, ChatGroup>
    implements ChatGroupService{

    @Autowired
    GroupMemberService groupMemberService;

    @Autowired
    GroupMemberMapper groupMemberMapper;

    @Autowired
    StringRedisTemplate redisTemplate;

    @Override
    public void addGroup(GroupDto groupDto) {
        String userId = LoginUserHolder.getUserId();
        // 添加群组信息
        ChatGroup chatGroup = new ChatGroup();

        chatGroup.setGroupName(groupDto.getGroupName());
        chatGroup.setCreateTime(LocalDateTime.now());
        chatGroup.setOwnerUserId(userId);

        save(chatGroup);

        // 添加好友群组信息
        GroupMember groupMember = new GroupMember();

        groupMember.setRole(2);
        groupMember.setJoinTime(LocalDateTime.now());
        groupMember.setGroupId(chatGroup.getId());
        groupMember.setUserId(userId);

        groupMemberService.save(groupMember);

        // 保存群聊列表信息到redis中
        String groupKey = GroupConstant.GROUP_KEY + userId;

        redisTemplate.opsForSet().add(groupKey, chatGroup.getId());
    }
    @Override
    public List<GroupVo> searchGroup(String keyword) {
        String userId = LoginUserHolder.getUserId();
        return baseMapper.searchGroupWithStatus(keyword, userId);
    }

    @Override
    public List<GroupVo> listGroup() {
        String userId = LoginUserHolder.getUserId();

        return groupMemberMapper.queryGroupByUserId(userId);
    }

    @Override
    public void applyGroup(String groupId, String reason) {
        String userId = LoginUserHolder.getUserId();

        // 1. 检查是否已经是成员
        GroupMember existingMember = groupMemberService.getOne(new LambdaQueryWrapper<GroupMember>()
                .eq(GroupMember::getGroupId, groupId)
                .eq(GroupMember::getUserId, userId));

        if (existingMember != null) {
            throw new RuntimeException("Already a member of this group");
        }

        joinGroup(groupId, userId);
    }


    private void joinGroup(String groupId, String userId) {
        GroupMember groupMember = new GroupMember();
        groupMember.setGroupId(groupId);
        groupMember.setUserId(userId);
        groupMember.setRole(1);
        groupMember.setJoinTime(LocalDateTime.now());
        groupMemberService.save(groupMember);

        // 更新Redis缓存
        String groupKey = GroupConstant.GROUP_KEY + userId;
        redisTemplate.opsForSet().add(groupKey, groupId);
    }
}





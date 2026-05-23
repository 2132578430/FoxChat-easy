package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.GroupMember;
import com.bedfox.service.mapper.GroupMemberMapper;
import com.bedfox.service.service.GroupMemberService;
import org.springframework.stereotype.Service;

/**
* @author 21325
* @description 针对表【group_member】的数据库操作Service实现
* @createDate 2026-02-21 20:20:25
*/
@Service
public class GroupMemberServiceImpl extends ServiceImpl<GroupMemberMapper, GroupMember>
    implements GroupMemberService{

}





package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.FriendsRequest;
import com.bedfox.service.mapper.FriendsRequestMapper;
import com.bedfox.service.service.FriendsRequestService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.pojo.vo.FriendVo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
* @author 21325
* @description 针对表【friends_request】的数据库操作Service实现
* @createDate 2026-02-13 21:06:40
*/
@Service
public class FriendsRequestServiceImpl extends ServiceImpl<FriendsRequestMapper, FriendsRequest>
    implements FriendsRequestService{

    @Autowired
    FriendsRequestMapper friendsRequestMapper;

    @Override
    public List<FriendVo> requestFriendList() {
        String acceptUserId = LoginUserHolder.getUserId();

        return friendsRequestMapper.requestFriendList(acceptUserId);
    }
}





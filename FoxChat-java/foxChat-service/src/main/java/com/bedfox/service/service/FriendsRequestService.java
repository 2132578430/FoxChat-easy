package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.FriendsRequest;
import com.bedfox.pojo.vo.FriendVo;

import java.util.List;

/**
* @author 21325
* @description 针对表【friends_request】的数据库操作Service
* @createDate 2026-02-13 21:06:40
*/
public interface FriendsRequestService extends IService<FriendsRequest> {

    List<FriendVo> requestFriendList();
}

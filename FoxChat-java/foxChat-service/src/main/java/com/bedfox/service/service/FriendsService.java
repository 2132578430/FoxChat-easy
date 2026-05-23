package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.Friends;
import com.bedfox.pojo.dto.AddFriendDto;
import com.bedfox.pojo.vo.FriendVo;

import java.util.List;

/**
* @author 21325
* @description 针对表【friends】的数据库操作Service
* @createDate 2026-02-13 01:14:44
*/
public interface FriendsService extends IService<Friends> {

    void addFriend(AddFriendDto addFriendDto);

    List<FriendVo> listFriends();

    /**
     * 获取所有好友（包含人类和 AI）
     * @return 好友列表
     */
    List<FriendVo> listAllFriends();

    void deleteFriend(String friendId, Integer role);
}

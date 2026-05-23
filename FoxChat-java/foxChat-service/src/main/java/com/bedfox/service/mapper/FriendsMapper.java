package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.Friends;
import com.bedfox.pojo.vo.FriendVo;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
* @author 21325
* @description 针对表【friends】的数据库操作Mapper
* @createDate 2026-02-13 01:14:44
* @Entity com.bedfox.bedfoxchat.domain.Friends
*/
public interface FriendsMapper extends BaseMapper<Friends> {

    List<FriendVo> listFriends(@Param("userId") String userId);

    void deleteFriend(@Param("userId") String userId, @Param("friendUserId") String friendUserId);
}





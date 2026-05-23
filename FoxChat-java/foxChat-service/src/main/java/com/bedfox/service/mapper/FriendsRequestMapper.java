package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.FriendsRequest;
import com.bedfox.pojo.vo.FriendVo;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
* @author 21325
* @description 针对表【friends_request】的数据库操作Mapper
* @createDate 2026-02-13 21:06:40
* @Entity com.bedfox.bedfoxchat.domain.FriendsRequest
*/
public interface FriendsRequestMapper extends BaseMapper<FriendsRequest> {

    List<FriendVo> requestFriendList(@Param("acceptUserId") String acceptUserId);

    void deleteRequest(@Param("userId") String userId, @Param("friendUserId") String friendUserId);
}





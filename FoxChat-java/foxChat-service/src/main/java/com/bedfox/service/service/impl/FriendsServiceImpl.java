package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.common.constant.*;
import com.bedfox.pojo.domain.CurrentUser;
import com.bedfox.pojo.domain.Friends;
import com.bedfox.pojo.dto.AddFriendDto;
import com.bedfox.common.exception.BusinessException;
import com.bedfox.service.mapper.FriendsMapper;
import com.bedfox.service.mapper.FriendsRequestMapper;
import com.bedfox.service.service.FriendsService;
import com.bedfox.service.service.LlmUserService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.pojo.vo.FriendVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Stream;

/**
* @author 21325
* @description 针对表【friends】的数据库操作Service实现
* @createDate 2026-02-13 01:14:44
*/
@Slf4j
@Service
public class FriendsServiceImpl extends ServiceImpl<FriendsMapper, Friends>
    implements FriendsService{

    @Resource
    FriendsMapper friendsMapper;

    @Resource
    FriendsRequestMapper friendsRequestMapper;

    @Resource
    LlmUserService llmUserService;

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    /**
     * 添加好友
     * @param addFriendDto
     */
    @Transactional
    @Override
    public void addFriend(AddFriendDto addFriendDto) {
        if (addFriendDto == null || addFriendDto.getFriendUserId() == null) {
            throw new BusinessException(ResultStatusConstant.FRIEND_NO_EXIST_EXCEPTION);
        }

        CurrentUser currentUser = LoginUserHolder.getUser();
        String userId = currentUser.getUserId();
        String friendUserId = addFriendDto.getFriendUserId();

        Friends friends = new Friends();
        friends.setUserId(userId);
        friends.setFriendUserId(friendUserId);

        Friends otherFriends = new Friends();
        otherFriends.setUserId(friendUserId);
        otherFriends.setFriendUserId(userId);

        // 移除请求数据
        friendsRequestMapper.deleteRequest(userId, friendUserId);

        // 保存两份双向数据
        saveBatch(List.of(friends, otherFriends));

        // 利用lua保存到redis中
        String userKey = FriendConstant.USER_FRIEND_PRE + userId;
        String friendKey = FriendConstant.USER_FRIEND_PRE + friendUserId;

        RedisScript<Integer> script = new DefaultRedisScript<>(LuaConstant.ADD_FRIEND, Integer.class);
        redisTemplate.execute(script, List.of(userKey, friendKey), friendKey, userKey);
    }

    /**
     * 展示好友列表
     *
     * @return
     */
    @Override
    public List<FriendVo> listFriends() {
        CurrentUser currentUser = LoginUserHolder.getUser();
        String userId = currentUser.getUserId();

        List<FriendVo> userList = friendsMapper.listFriends(userId);

        return userList.stream()
                .peek(friendVo -> {
                    Boolean isOnline = redisTemplate.hasKey(AuthConstant.PRE_ONLINE + friendVo.getUserId());
                    friendVo.setOnline(isOnline != null && isOnline);
                    friendVo.setRole(ChatRoleConstant.HUMAN);
                })
                .toList();
    }

    @Override
    public List<FriendVo> listAllFriends() {
        List<FriendVo> friendList = listFriends();

        List<FriendVo> llmList = llmUserService
                .friendList(LoginUserHolder.getUserId());

        return Stream.concat(friendList.stream(), llmList.stream()).toList();
    }

    /**
     * 删除好友
     * 包括数据库和redis
     *
     * @param friendUserId 好友id
     * @param role
     */
    @Override
    public void deleteFriend(String friendUserId, Integer role) {
        if (role.equals(ChatRoleConstant.LLM)) {
            log.info("删除模型");
            llmUserService.deleteFriend(friendUserId);
            return ;
        }


        String userId = LoginUserHolder.getUserId();

        friendsMapper.deleteFriend(userId, friendUserId);

        // 利用lua删除字段
        String userKey = FriendConstant.USER_FRIEND_PRE + userId;
        String friendKey = FriendConstant.USER_FRIEND_PRE + friendUserId;

        RedisScript<Integer> script = new DefaultRedisScript<>(LuaConstant.DELETE_FRIEND, Integer.class);
        redisTemplate.execute(script, List.of(userKey, friendKey), friendKey, userKey);
    }
}





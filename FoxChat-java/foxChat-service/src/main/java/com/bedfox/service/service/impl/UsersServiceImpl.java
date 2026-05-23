package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.common.constant.AuthConstant;
import com.bedfox.common.constant.FileContstant;
import com.bedfox.pojo.domain.Friends;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.SearchUserDto;
import com.bedfox.pojo.dto.UpdateUserDto;
import com.bedfox.service.mapper.UsersMapper;
import com.bedfox.service.service.FriendsService;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.MinioUtil;
import com.bedfox.pojo.vo.SearchUserVo;
import com.bedfox.pojo.vo.SelectFriendVo;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
* @author 21325
* @description 针对表【users】的数据库操作Service实现
* @createDate 2026-02-12 00:49:01
*/
@Service
public class UsersServiceImpl extends ServiceImpl<UsersMapper, Users>
    implements UsersService{

    @Autowired
    FriendsService friendsService;

    @Autowired
    MinioUtil minioUtil;

    @Autowired
    StringRedisTemplate redisTemplate;

    /**
     * 根据username获取用户
     *
     * @param searchUserDto
     * @return
     */
    @Override
    public List<SearchUserVo> searchFriend(SearchUserDto searchUserDto) {
        String searchName = searchUserDto.getNickname();

        List<Users> userList = list(new LambdaQueryWrapper<Users>()
                .like(Users::getNickname, "%" + searchName + "%")
                .or()
                .like(Users::getUsername, "%" + searchName + "$"));

        String userId = LoginUserHolder.getUserId();

        List<Friends> friendList = friendsService.list(new LambdaQueryWrapper<Friends>().eq(Friends::getUserId, userId));

        // 将该用户所有的好友id建立Set集合
        Set<String> friendsSet = new HashSet<>(friendList.stream().map(Friends::getFriendUserId).toList());

        return userList.stream()
                .filter(users -> !users.getId().equals(userId))
                .map(user -> {
                    SearchUserVo searchUserVo = new SearchUserVo();
                    searchUserVo.setUserId(user.getId());
                    searchUserVo.setUsername(user.getUsername());
                    searchUserVo.setFaceImage(user.getFaceImage());
                    searchUserVo.setNickname(user.getNickname());
                    searchUserVo.setIsFriend(friendsSet.contains(user.getId()));
                    return searchUserVo;
                }).toList();
    }

    /**
     * 根据用户id返回对应图像等数据
     * @param friendId
     * @return
     */
    @Override
    public SelectFriendVo selectUser(String friendId) {
        Users user = getById(friendId);
        SelectFriendVo friendVo = new SelectFriendVo();

        BeanUtils.copyProperties(user, friendVo);

        Boolean isOnline = redisTemplate.hasKey(AuthConstant.PRE_ONLINE + friendId);

        friendVo.setUserId(user.getId());
        friendVo.setOnline(isOnline != null && isOnline);

        return friendVo;
    }

    /**
     * 修改用户信息
     * @param updateUserDto
     */
    @Override
    public void updateUser(UpdateUserDto updateUserDto) {
        Users users = new Users();

        BeanUtils.copyProperties(updateUserDto, users);
        users.setId(LoginUserHolder.getUserId());

        updateById(users);
    }

    /**
     * 修改文件路径
     * @param avatarFile
     * @return
     */
    @Override
    public String updateAvatar(MultipartFile avatarFile) {
        String userId = LoginUserHolder.getUserId();

        // 将文件上传到miniO服务器
        String fileUrl = minioUtil.uploadFile(avatarFile, FileContstant.CHAT_BIZPATH, userId);

        // 更新数据库头像url
        Users user = new Users();

        user.setId(LoginUserHolder.getUserId());
        user.setFaceImage(fileUrl);

        updateById(user);

        return fileUrl;
    }

    @Override
    public Users buildSender(String userId) {
        //TODO:引入redis缓存
        return getById(userId);
    }
}





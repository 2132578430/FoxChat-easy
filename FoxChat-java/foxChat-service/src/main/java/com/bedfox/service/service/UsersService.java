package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.SearchUserDto;
import com.bedfox.pojo.dto.UpdateUserDto;
import com.bedfox.pojo.vo.SearchUserVo;
import com.bedfox.pojo.vo.SelectFriendVo;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
* @author 21325
* @description 针对表【users】的数据库操作Service
* @createDate 2026-02-12 00:49:01
*/
public interface UsersService extends IService<Users> {

    List<SearchUserVo> searchFriend(SearchUserDto searchUserDto);

    SelectFriendVo selectUser(String friendId);

    void updateUser(UpdateUserDto updateUserDto);

    String updateAvatar(MultipartFile avatarFile);

    Users buildSender(String sender);
}

package com.bedfox.web.controller;

import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.UpdateUserDto;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.ShowUserInfo;
import jakarta.annotation.Resource;
import org.springframework.beans.BeanUtils;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

/**
 * @author bedFox
 */
@RestController
@RequestMapping("/user")
public class UserController {

    @Resource
    UsersService usersService;

    /**
     * 查询用户信息
     * @return
     */
    @GetMapping("/info")
    public R<ShowUserInfo> userInfo() {
        Users users = usersService.getById(LoginUserHolder.getUserId());

        ShowUserInfo showUserInfo = new ShowUserInfo();

        BeanUtils.copyProperties(users, showUserInfo);

        return R.ok(showUserInfo);
    }

    /**
     * 修改用户信息
     */
    @PostMapping("/update")
    public R<String> updateUser(@RequestBody UpdateUserDto updateUserDto) {
        usersService.updateUser(updateUserDto);
        return R.ok();
    }

    /**
     * 修改用户头像
     */
    @PostMapping("/updateAvatar")
    public R<String> updateAvatar(@RequestParam("file") MultipartFile avatarFile) {
        String avatarUrl = usersService.updateAvatar(avatarFile);

        return R.ok(avatarUrl);
    }

    /**
     * 获取用户当前头像url
     */
    @PostMapping("/avatar")
    public R<String> avatar() {
        String faceUrl = usersService.getById(LoginUserHolder.getUserId())
                .getFaceImage();

        return R.ok(faceUrl);
    }
}

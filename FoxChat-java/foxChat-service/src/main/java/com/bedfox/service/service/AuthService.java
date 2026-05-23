package com.bedfox.service.service;

import com.bedfox.pojo.dto.RegisterDto;
import com.bedfox.pojo.dto.UserDto;
import com.bedfox.pojo.vo.UserInfo;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * @author bedFox
 */
public interface AuthService {
    UserInfo login(UserDto userDto, HttpServletResponse response);

    void register(RegisterDto registerDto);

    void sendCode(String email);

    void logout(HttpServletRequest request, HttpServletResponse response);
}

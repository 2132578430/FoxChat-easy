package com.bedfox.web.controller;

import com.bedfox.pojo.dto.CodeDto;
import com.bedfox.pojo.dto.RegisterDto;
import com.bedfox.pojo.dto.UserDto;
import com.bedfox.service.service.AuthService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.UserInfo;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * @author bedFox
 */
@RestController
@RequestMapping("/auth")
public class AuthController {

    @Resource
    AuthService authService;

    /**
     * 登录接口
     *
     * 该方法处理用户登录请求，接收用户凭证信息并返回登录结果。
     *
     * @param userDto 包含用户登录凭证的DTO对象，通常包括用户名和密码等信息
     * @param response HttpServletResponse 用于设置 HTTPOnly cookie
     * @return 返回封装了用户信息的响应对象，若登录成功则包含用户详细信息，否则返回错误信息
     */
    @PostMapping("/login")
    public R<UserInfo> login(@RequestBody UserDto userDto, HttpServletResponse response) {
        // 调用认证服务进行登录验证，并获取用户信息
        UserInfo userInfo = authService.login(userDto, response);

        // 将用户信息封装到统一响应对象中并返回
        return R.ok(userInfo);
    }

    /**
     * 处理用户注册请求的接口方法。
     *
     * @param registerDto 包含用户注册信息的数据传输对象，通常包括用户名、密码等字段。
     * @return 返回一个通用响应对象R<UserInfo>，表示注册操作的结果。成功时返回R.ok()，
     *         其中UserInfo可能包含注册成功的用户基本信息（具体取决于R.ok()的实现）。
     */
    @PostMapping("/register")
    public R<UserInfo> register(@RequestBody RegisterDto registerDto) {
        // 调用认证服务完成用户注册逻辑
        authService.register(registerDto);
        // 返回注册成功的响应结果
        return R.ok();
    }

    /**
     * 发送验证码
     * @param codeDto
     * @return
     */
    @PostMapping("/sendCode")
    public R<String> sendCode(@RequestBody CodeDto codeDto) {
        authService.sendCode(codeDto.getEmail());
        return R.ok();
    }

    /**
     * 登出接口 - 清除 cookie 和 Redis token
     * @param request
     * @param response
     * @return
     */
    @PostMapping("/logout")
    public R<Void> logout(HttpServletRequest request, HttpServletResponse response) {
        authService.logout(request, response);
        return R.ok();
    }

}

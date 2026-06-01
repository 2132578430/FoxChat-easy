package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.bedfox.common.constant.AuthConstant;
import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.pojo.domain.Users;
import com.bedfox.pojo.dto.RegisterDto;
import com.bedfox.pojo.dto.UserDto;
import com.bedfox.common.exception.BusinessException;
import com.bedfox.service.service.AuthService;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.CookieUtil;
import com.bedfox.common.util.JwtUtil;
import com.bedfox.pojo.vo.UserInfo;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * @author bedFox
 */
@Slf4j
@Service
public class AuthServiceImpl implements AuthService {

    @Resource
    UsersService usersService;

    @Resource(name = "stringRedisTemplate")
    StringRedisTemplate redisTemplate;

    @Resource
    PasswordEncoder passwordEncoder;

    @Resource
    JwtUtil jwtUtil;

    /**
     * 登录接口
     * @param userDto
     * @param response
     * @return
     */
    @Override
    public UserInfo login(UserDto userDto, HttpServletResponse response) {
        UserInfo userInfo = new UserInfo();
        String username = userDto.getUsername();
        String password = userDto.getPassword();

        // 账户或密码不存在
        if (StringUtils.isAnyEmpty(username, password)) {
            throw new BusinessException(ResultStatusConstant.LOGIN_FORMAT_ERROR_EXCEPTION);
        }

        // 从数据库查询用户
        Users users = usersService.getOne(new LambdaQueryWrapper<Users>().eq(Users::getUsername, username));

        // 不存在用户
        if (users == null) {
            throw new BusinessException(ResultStatusConstant.LOGIN_ACCOUNT_NOT_EXIST_EXCEPTION);
        }

        String dbPassword = users.getPassword();
        String dbUserId = users.getId();

        // 加密密码匹配
        boolean match = passwordEncoder.matches(password, dbPassword);

        // 密码错误
        if (!match) {
            throw new BusinessException(ResultStatusConstant.LOGIN_PASSWORD_ERROR_EXCEPTION);
        }

        // 生成用户token
        String token = jwtUtil.generateToken(dbUserId);

        // 将token有效内容存入redis
        String tokenKey = AuthConstant.PRE_LOGIN_AUTH + token;
        redisTemplate.opsForValue().set(tokenKey, username, 24, TimeUnit.HOURS);

        // 为响应值设置 HTTPOnly cookie
        CookieUtil.setTokenCookie(response, token);

        // 组合结果
        userInfo.setUserId(dbUserId);
        userInfo.setUsername(username);
        userInfo.setToken(null);

        return userInfo;
    }

    /**
     * 注册方法
     * @param registerDto
     */
    @Override
    public void register(RegisterDto registerDto) {
        Users users = new Users();
        String nickName = registerDto.getNickname();
        String userName = registerDto.getUsername();
        String password = registerDto.getPassword();

        // 检验数据完整符合规定
        if (StringUtils.isAnyEmpty(nickName, userName, password)) {
            throw new BusinessException(ResultStatusConstant.REGISTER_FORMAT_ERROR_EXCEPTION);
        }

        // 检查用户名是否重复
        long count = usersService.count(new LambdaQueryWrapper<Users>().eq(Users::getUsername, userName));

        if (count > 0) {
            throw new BusinessException(ResultStatusConstant.REGISTER_USER_REPEAT_EXCEPTION);
        }

        users.setUsername(userName);
        users.setNickname(nickName);

        // 密码加密
        String encodePassword = passwordEncoder.encode(password);
        users.setPassword(encodePassword);

        usersService.save(users);
    }

    /**
     * 登出 - 清除 cookie 和 Redis token
     * @param request
     * @param response
     */
    @Override
    public void logout(HttpServletRequest request, HttpServletResponse response) {
        String token = CookieUtil.getTokenFromCookie(request);
        if (token != null) {
            // 删除 Redis 中的 token
            String tokenKey = AuthConstant.PRE_LOGIN_AUTH + token;
            redisTemplate.delete(tokenKey);
        }
        // 清除 cookie
        CookieUtil.clearTokenCookie(response);
    }
}

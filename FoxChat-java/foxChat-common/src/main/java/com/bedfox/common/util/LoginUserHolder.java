package com.bedfox.common.util;

import com.bedfox.pojo.domain.CurrentUser;

/**
 * 登录身份校验类
 *
 * @author bedFox
 * @date 2026/3/23 08:18
 */
public class LoginUserHolder {
    public static ThreadLocal<CurrentUser> userThreadLocal = new ThreadLocal<>();

    public static void setCurrent(CurrentUser user) {
        userThreadLocal.set(user);
    }

    public static CurrentUser getUser() {
        return userThreadLocal.get();
    }

    public static String getUserId() {
        return userThreadLocal.get().getUserId();
    }

    public static String getUserName() {
        return userThreadLocal.get().getUserName();
    }

    public static void clear() {
        userThreadLocal.remove();
    }
}

package com.bedfox.common.util;

import com.bedfox.common.constant.ResultStatusConstant;
import lombok.Data;

/**
 * @author bedFox
 * @
 */
@Data
public class R<T> {
    private Integer code;
    private String msg;
    private T data;

    public R(Integer code, String msg, T data) {
        this.code = code;
        this.msg = msg;
        this.data = data;
    }

    public R() {}

    public static <t> R<t> ok(t data) {
        return new R<>(ResultStatusConstant.SUCCESS.getCode(),
                ResultStatusConstant.SUCCESS.getMsg(),
                data);
    }

    public static <t> R<t> ok() {
        return new R<>(ResultStatusConstant.SUCCESS.getCode(),
                ResultStatusConstant.SUCCESS.getMsg(),
                null);
    }

    public static <t> R<t> error(Integer code, String msg) {
        return new R<>(code, msg, null);
    }

    public static <t> R<t> error(ResultStatusConstant status) {
        return new R<>(status.getCode(), status.getMsg(), null);
    }

    public static <t> R<t> error(ResultStatusConstant status, t data) {
        return new R<>(status.getCode(), status.getMsg(), data);
    }

    public static <t> R<t> error() {
        return new R<>(ResultStatusConstant.UNKNOWN_ERROR.getCode(),
                ResultStatusConstant.UNKNOWN_ERROR.getMsg(),
                null);
    }
}

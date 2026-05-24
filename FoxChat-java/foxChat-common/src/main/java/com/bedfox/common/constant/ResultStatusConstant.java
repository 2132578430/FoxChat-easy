package com.bedfox.common.constant;

import lombok.Getter;

/**
 * @author bedFox
 * 10 - 统一接口服务
 *  00 - 成功
 *  01 - 失败
 * 110 - 登录业务错误
 *  00 - 账号或密码不符合格式
 *  01 - 账户不存在
 *  02 - 密码错误
 *  03 - 验证码错误
 * 120 - 注册业务错误
 *  00 - 账号或密码不符合格式
 *  01 - 验证码错误
 *  02 - 验证码过于频繁
 * 130 - 好友业务错误
 *  00 - 好友不存在
 * 140 - 文件储存业务错误
 *  00 - 文件上传失败
 *  01 - 文件上传重复
 * 200 - 内网请求错误
 *  00 - 内网信息发送缺失
 *
 */
@Getter
public enum ResultStatusConstant {
    // 统一服务状态
    SUCCESS(1000, "响应成功"),
    UNKNOWN_ERROR(1001, "未知错误"),

    // 登录服务状态异常
    LOGIN_FORMAT_ERROR_EXCEPTION(11000, "登录账号或密码不符合格式"),
    LOGIN_ACCOUNT_NOT_EXIST_EXCEPTION(11001, "账户不存在"),
    LOGIN_PASSWORD_ERROR_EXCEPTION(11002, "密码错误"),
    LOGIN_CODE_ERROR_EXCEPTION(11003, "验证码错误"),

    // 注册服务状态异常
    REGISTER_FORMAT_ERROR_EXCEPTION(12000, "登录账号或密码不符合格式"),
    REGISTER_CODE_ERROR_EXCEPTION(12001,"验证码错误"),
    REGISTER_CODE_REPEAT_EXCEPTION(12002, "请勿重复发送验证码"),
    REGISTER_USER_REPEAT_EXCEPTION(12003, "邮箱或用户名重复"),

    // 好友服务状态异常
    FRIEND_NO_EXIST_EXCEPTION(13000, "好友不存在"),

    // 文件上传状态异常
    FILE_UPLOAD_ERROR_EXCEPTION(14000, "文件上传失败"),

    // 内网工作异常
    RAG_MSG_ERROR_EXCEPTION(20000, "rag数据库内网消息传输错误"),

    // ============================================================
    // LLM 配置服务错误 (15XXX)
    // ============================================================

    /** 未完成所有模型配置 */
    LLM_CONFIG_INCOMPLETE_EXCEPTION(15001, "未完成所有模型配置，请前往设置页面完成配置"),

    /** API Key 无效 */
    LLM_API_KEY_INVALID_EXCEPTION(15002, "API Key 无效或已过期"),

    /** 模型不存在 */
    LLM_MODEL_NOT_FOUND_EXCEPTION(15003, "模型不存在或服务商不支持该模型"),

    /** 网络错误 */
    LLM_NETWORK_ERROR_EXCEPTION(15004, "连接超时，请检查网络或 Base URL"),

    /** 配额已用尽 */
    LLM_RATE_LIMIT_EXCEPTION(15005, "API 配额已用尽，请检查您的账户"),

    /** 配置保存失败 */
    LLM_CONFIG_SAVE_ERROR_EXCEPTION(15006, "配置保存失败"),

    /** 创造物已激活或正在处理中 */
    LLM_ALREADY_ACTIVATED_EXCEPTION(15007, "创造物已激活或正在处理中"),

    /** 创造物不存在 */
    LLM_NOT_FOUND_EXCEPTION(15008, "创造物不存在"),

    /** 无权限操作该创造物 */
    LLM_NOT_OWNER_EXCEPTION(15009, "无权限操作该创造物"),

    /** 思考中 */
    LLM_PROCESSING(20001, "思考中..."),

    /** 回复失败 */
    LLM_FAILED(20002, "回复失败");

    private Integer code;
    private String msg;

    ResultStatusConstant(Integer code, String msg) {
        this.code = code;
        this.msg = msg;
    }

    ResultStatusConstant() {
    }
}

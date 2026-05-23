package com.bedfox.common.util;

import com.alibaba.fastjson2.JSON;
import lombok.Data;
import org.apache.commons.codec.digest.DigestUtils;

import java.io.Serializable;

/**
 * 内网传递消息类
 *
 * @author bedFox
 * @date 2026/3/15 11:59
 */
@Data
public class M<T> implements Serializable {
    private String msgId;

    private T data;

    public M(String msgId, T data) {
        this.msgId = msgId;
        this.data = data;
    }

    /**
     * 包装data为M类，同时自动生成msgId保证幂等性
     * @param data 需要封装的数据
     * @return 返回M
     */
    public static  <t> M<t> getMsg(t data) {
        String dataJson = JSON.toJSONString(data);

        String msgId = DigestUtils.md5Hex(dataJson);

        return new M<>(msgId, data);
    }
}

package com.bedfox.netty.netty;

import io.netty.channel.Channel;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 作为全局的用户id和channel通道对应
 *
 * @author bedFox
 */
public class UserChannelRelation {
    public static Map<String, Channel> manager = new ConcurrentHashMap<>();

    public static void put(String userId, Channel channel) {
        manager.put(userId, channel);
    }

    public static Channel get(String userId) {
        return manager.get(userId);
    }

    public static void remove(String userId) {
        manager.remove(userId);
    }

    /**
     * 原子性地移除指定 userId 对应的 channel。
     * 只有当 map 中该 userId 对应的 channel 与传入的 channel 为同一实例时才移除，
     * 避免误删其他连接（如多设备登录场景）。
     */
    public static void remove(String userId, Channel channel) {
        manager.computeIfPresent(userId, (key, existingChannel) -> {
            if (existingChannel.isOpen() && existingChannel.id().equals(channel.id())) {
                return null; // 返回 null 表示移除该条目
            }
            return existingChannel; // 保留现有条目
        });
    }

    public static void output() {
        for (Map.Entry<String, Channel> entry : manager.entrySet()) {
            System.out.println("user:" + entry.getKey() + ", channel:" + entry.getValue().id());
        }
    }
}

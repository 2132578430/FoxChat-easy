package com.bedfox.netty.netty;

import io.netty.channel.Channel;

import java.util.HashMap;
import java.util.Map;

/**
 * 作为全局的用户id和channel通道对应
 *
 * @author bedFox
 */
public class UserChannelRelation {
    public static Map<String, Channel> manager = new HashMap<>();

    public static void put(String userId, Channel channel) {
        manager.put(userId, channel);
    }

    public static Channel get(String userId) {
        return manager.get(userId);
    }

    public static void remove(String userId) {
        manager.remove(userId);
    }

    public static void remove(String userId, Channel channel) {
        Channel userChannel = manager.get(userId);

        if (userChannel == null || !userChannel.isOpen()) {
            return ;
        }

        if (userChannel.id().equals(channel.id())) {
            manager.remove(userId);
        }
    }

    public static void output() {
        for (Map.Entry<String, Channel> entry : manager.entrySet()) {
            System.out.println("user:" + entry.getKey() + ", channel:" + entry.getValue().id());
        }
    }
}

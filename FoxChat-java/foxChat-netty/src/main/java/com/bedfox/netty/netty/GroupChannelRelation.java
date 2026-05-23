package com.bedfox.netty.netty;

import io.netty.channel.Channel;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.util.concurrent.GlobalEventExecutor;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author bedFox
 */
public class GroupChannelRelation {
    private static Map<String, ChannelGroup> groupManager = new ConcurrentHashMap<>();

    /**
     * 向group管理器中放入group
     * @param groupId
     * @param group
     */
    public static void add(String groupId, ChannelGroup group) {
        groupManager.put(groupId, group);
    }


    public static ChannelGroup get(String groupId) {
        return groupManager.get(groupId);
    }
    /**
     * 向管理器中放入用户Channel
     */
    public static void addUser(String groupId, Channel userChannel) {
        ChannelGroup group = groupManager.get(groupId);

        // 没有group就创建出来
        if (group == null) {
            group = new DefaultChannelGroup(GlobalEventExecutor.INSTANCE);

            groupManager.put(groupId, group);
        }

        group.add(userChannel);
    }

    /**
     * 移除用户
     * @param groupId
     * @param userChannel
     */
    public static void removeUser(String groupId, Channel userChannel) {
        ChannelGroup group = groupManager.get(groupId);

        if (group != null) {
            group.remove(userChannel);

            if (group.isEmpty()) {
                groupManager.remove(groupId);
            }
        }
    }


}

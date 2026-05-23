package com.bedfox.common.constant;

/**
 * @author bedFox
 * @date 2026/3/20 20:46
 */
public class LuaConstant {
    public final static String DELETE_FRIEND = """
            redis.call('SREM', KEYS[1], ARGV[1])
            redis.call('SREM', KEYS[2], ARGV[2])
            return 1
            """;

    public final static String ADD_FRIEND = """
            redis.call('SADD', KEYS[1], ARGV[1])
            redis.call('SADD', KEYS[2], ARGV[2])
            return 1
            """;
}

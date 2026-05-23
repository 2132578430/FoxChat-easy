package com.bedfox.common.util;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

/**
 * 时间戳转化工具
 *
 * @author bedFox
 */
public class TimeUtil {
    public static LocalDateTime timestampToLdt(Long timestamp) {
        if (timestamp == null) {
            return LocalDateTime.now();
        }

        Instant instant = Instant.ofEpochMilli(timestamp);

        return LocalDateTime.ofInstant(instant, ZoneId.of("Asia/Shanghai"));
    }

    public static Long ldtToTimestamp(LocalDateTime dateTime) {
        if (dateTime == null) {
            return 0L;
        }

        return dateTime.atZone(ZoneId.of("Asia/Shanghai"))
                .toInstant()
                .toEpochMilli();
    }
}

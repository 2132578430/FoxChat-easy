package com.bedfox.common.util;

import java.security.SecureRandom;

/**
 * @author bedFox
 */
public class CodeUtil {
    private static final SecureRandom RANDOM = new SecureRandom();

    public static String generateCode() {
        return String.format("%06d", RANDOM.nextInt(1_000_000));
    }
}

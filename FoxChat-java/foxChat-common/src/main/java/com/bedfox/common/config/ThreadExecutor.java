package com.bedfox.common.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * @author bedFox
 * @date 2026/3/18 15:14
 */
@Configuration
public class ThreadExecutor {

    @Value("${Executor.corePoolSize}")
    public int corePoolSize;

    @Value("${Executor.maxPoolSize}")
    public int maxPoolSize;

    @Value("${Executor.queueCapacity}")
    public int queueCapacity;

    @Bean
    public ThreadPoolExecutor executor() {
        return new ThreadPoolExecutor(
                corePoolSize,
                maxPoolSize,
                60,
                TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(queueCapacity)
        );
    }
}

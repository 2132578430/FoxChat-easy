package com.bedfox.service.health;

import com.bedfox.service.client.grpc.GrpcChatClient;
import io.grpc.ConnectivityState;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * gRPC Python 服务健康检查
 *
 * 通过 GrpcChatClient 的 ManagedChannel 检查与 Python gRPC Server 的连接状态：
 *   - READY      → UP
 *   - CONNECTING → UP（正在建连，视为可用）
 *   - IDLE       → UP（空闲，gRPC 会在下次调用时自动重连）
 *   - TRANSIENT_FAILURE → DOWN（连接失败）
 *   - SHUTDOWN   → DOWN（已关闭）
 *
 * 暴露在 /actuator/health 的 components.gRPC-Python 中
 *
 * @author bedFox
 */
@Slf4j
@Component
public class PythonGrpcHealthIndicator implements HealthIndicator {

    @Resource
    private GrpcChatClient grpcChatClient;

    @Override
    public Health health() {
        try {
            var channel = grpcChatClient.getChannel();
            if (channel == null) {
                return Health.down()
                    .withDetail("error", "ManagedChannel 未初始化")
                    .build();
            }

            ConnectivityState state = channel.getState(true);
            return switch (state) {
                case READY -> Health.up()
                    .withDetail("host", "gRPC Python Server")
                    .withDetail("state", state.name())
                    .build();
                case CONNECTING, IDLE -> Health.up()
                    .withDetail("host", "gRPC Python Server")
                    .withDetail("state", state.name())
                    .withDetail("note", "连接空闲/建立中，下次调用自动恢复")
                    .build();
                case TRANSIENT_FAILURE -> Health.down()
                    .withDetail("host", "gRPC Python Server")
                    .withDetail("state", state.name())
                    .withDetail("action", "请检查 Python gRPC Server (端口 50051) 是否运行")
                    .build();
                case SHUTDOWN -> Health.down()
                    .withDetail("host", "gRPC Python Server")
                    .withDetail("state", state.name())
                    .withDetail("action", "Channel 已关闭，请重启应用")
                    .build();
            };
        } catch (Exception e) {
            log.error("[HealthCheck] gRPC-Python 检查异常", e);
            return Health.down()
                .withDetail("error", e.getMessage())
                .build();
        }
    }
}

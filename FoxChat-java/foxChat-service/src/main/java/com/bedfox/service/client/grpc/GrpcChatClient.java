package com.bedfox.service.client.grpc;

import com.bedfox.pojo.proto.ai.AiChatProto;
import com.bedfox.pojo.proto.ai.AIChatServiceGrpc;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * gRPC 流式聊天客户端
 *
 * 职责：
 * - 建立到 Python gRPC Server 的 ManagedChannel
 * - 发送 ChatRequest，通过 StreamObserver 接收逐 token 的 ChatResponse
 * - 将每个 token 通过 onToken 回调传给 Netty Handler
 * - onError 时降级到 REST（ChatClient Feign）
 *
 * @author bedFox
 */
@Slf4j
@Component
public class GrpcChatClient {

    @Value("${grpc.python-host:localhost}")
    private String host;

    @Value("${grpc.python-port:50051}")
    private int port;

    private ManagedChannel channel;
    private AIChatServiceGrpc.AIChatServiceStub asyncStub;

    @PostConstruct
    public void init() {
        channel = ManagedChannelBuilder
            .forAddress(host, port)
            .usePlaintext()
            .keepAliveTime(30, TimeUnit.SECONDS)
            .keepAliveTimeout(10, TimeUnit.SECONDS)
            .keepAliveWithoutCalls(true)
            .maxInboundMessageSize(10 * 1024 * 1024)
            .build();

        asyncStub = AIChatServiceGrpc.newStub(channel);
        log.info("[gRPC Client] 已连接 {}:{}", host, port);
    }

    /**
     * 流式 Chat
     *
     * @param userId     用户ID
     * @param llmId      模型ID
     * @param message    用户消息
     * @param onToken    每个 ChatResponse 的回调（由 Netty Handler 写 WebSocket）
     * @param onComplete 流正常结束回调
     * @param onError    流异常回调（上层调用 REST 降级）
     */
    public void streamChat(
        String userId,
        String llmId,
        String message,
        Consumer<AiChatProto.ChatResponse> onToken,
        Runnable onComplete,
        Consumer<Throwable> onError
    ) {
        AiChatProto.ChatRequest request = AiChatProto.ChatRequest.newBuilder()
            .setUserId(userId)
            .setLlmId(llmId)
            .setMsgContent(message)
            .build();

        log.info("[gRPC Chat] 发起流式请求: user={}, llm={}, msg={}",
            userId.substring(0, Math.min(8, userId.length())),
            llmId.substring(0, Math.min(8, llmId.length())),
            message.substring(0, Math.min(30, message.length())));

        asyncStub.chat(request, new StreamObserver<>() {
            @Override
            public void onNext(AiChatProto.ChatResponse response) {
                if (response.getIsFinal()) {
                    log.debug("[gRPC Chat] 收到最终包: emotion={}", response.getEmotion());
                }
                onToken.accept(response);
                if (response.getIsFinal()) {
                    onComplete.run();
                }
            }

            @Override
            public void onError(Throwable t) {
                log.error("[gRPC Chat] 流式错误: {}", t.getMessage());
                onError.accept(t);
            }

            @Override
            public void onCompleted() {
                log.debug("[gRPC Chat] 流结束");
            }
        });
    }

    @PreDestroy
    public void shutdown() throws InterruptedException {
        if (channel != null && !channel.isShutdown()) {
            log.info("[gRPC Client] 关闭连接");
            channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}

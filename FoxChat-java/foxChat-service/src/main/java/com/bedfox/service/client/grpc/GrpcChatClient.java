package com.bedfox.service.client.grpc;

import com.bedfox.pojo.proto.ai.AiChatProto;
import com.bedfox.pojo.proto.ai.AIChatServiceGrpc;
import com.bedfox.service.grpc.ChatStreamObserver;
import io.grpc.ConnectivityState;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
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
            .idleTimeout(60, TimeUnit.SECONDS)  // 空闲 60s 断开，下次调用自动重连
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

        // [DIAG] 记录 channel 状态（true = 等待连接就绪）
        ConnectivityState state = channel.getState(true);
        log.info("[gRPC Chat] 发起流式请求: user={}, llm={}, msg={}, channelState={}, thread={}",
            userId,llmId,message,state,Thread.currentThread().getName());

        // 调用聊天方法
        asyncStub.withDeadlineAfter(120, TimeUnit.SECONDS)  // 总超时 120s（含 LLM 推理时间）
            .chat(request, new ChatStreamObserver(onToken, onComplete, onError, channel));

        log.info("[gRPC Chat] asyncStub.chat() 已派发, thread={}", Thread.currentThread().getName());
    }

    @PreDestroy
    public void shutdown() throws InterruptedException {
        if (channel != null && !channel.isShutdown()) {
            log.info("[gRPC Client] 关闭连接");
            channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}

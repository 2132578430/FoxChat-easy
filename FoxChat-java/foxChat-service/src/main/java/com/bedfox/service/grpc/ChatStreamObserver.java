package com.bedfox.service.grpc;

import io.grpc.ManagedChannel;
import io.grpc.stub.StreamObserver;
import org.springframework.stereotype.Component;

import com.bedfox.pojo.proto.ai.AiChatProto;
import io.grpc.ConnectivityState;
import io.grpc.StatusRuntimeException;
import io.micrometer.core.instrument.Counter;
import lombok.extern.slf4j.Slf4j;

import java.util.function.Consumer;

@Slf4j
public class ChatStreamObserver implements StreamObserver<AiChatProto.ChatResponse> {
    private boolean firstTokenReceived = false;

    private final Consumer<AiChatProto.ChatResponse> onToken;
    private final Runnable onComplete;
    private final Consumer<Throwable> onError;
    private final ManagedChannel channel;
    private final Counter errorCounter;

    public ChatStreamObserver(
            Consumer<AiChatProto.ChatResponse> onToken,
            Runnable onComplete,
            Consumer<Throwable> onError,
            ManagedChannel channel,
            Counter errorCounter
    ) {
        this.onToken = onToken;
        this.onComplete = onComplete;
        this.onError = onError;
        this.channel = channel;
        this.errorCounter = errorCounter;
    }

    @Override
    public void onNext(AiChatProto.ChatResponse response) {
        if (!firstTokenReceived) {
            firstTokenReceived = true;
            log.info("[gRPC Chat] 收到首 token: seq={}", response.getSequence());
        }
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
        // Metrics: 记录错误
        errorCounter.increment();

        // [DIAG] 追加 gRPC 状态码和 channel 状态
        String statusCode = "UNKNOWN";
        if (t instanceof StatusRuntimeException sre) {
            statusCode = sre.getStatus().getCode().name();
        }
        ConnectivityState cs = channel.getState(false);
        log.error("[gRPC Chat] 流式错误: status={}, channelState={}, msg={}",
            statusCode, cs, t.getMessage());
        onError.accept(t);
    }

    @Override
    public void onCompleted() {
        log.debug("[gRPC Chat] 流结束");
    }
}
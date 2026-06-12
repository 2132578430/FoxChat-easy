package com.bedfox.netty.handler.impl;

import com.alibaba.fastjson2.JSON;
import com.bedfox.common.constant.MsgTypeConstant;
import com.bedfox.netty.netty.ChatWebSocketHandler;
import com.bedfox.pojo.domain.ChatProtocol;
import com.bedfox.pojo.dto.MsgDto;
import com.bedfox.pojo.proto.ai.AiChatProto;
import com.bedfox.service.client.grpc.GrpcChatClient;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.util.Attribute;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.Map;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * LlmStreamHandler 单元测试
 *
 * 完全本地运行，不依赖任何服务器、数据库、网络。
 * 用 Mockito 模拟所有外部依赖 (ChannelHandlerContext / GrpcChatClient)。
 *
 * 运行方式：
 *   cd FoxChat-java
 *   ./gradlew :foxChat-netty:test --tests "com.bedfox.netty.handler.impl.LlmStreamHandlerTest"
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class LlmStreamHandlerTest {

    @Mock GrpcChatClient grpcClient;
    @Mock ChannelHandlerContext ctx;
    @Mock Channel channel;
    @Mock Attribute<String> userIdAttr;

    @InjectMocks LlmStreamHandler handler;

    @BeforeEach
    void setUp() {
        // 模拟从 Channel 拿 userId
        when(ctx.channel()).thenReturn(channel);
        when(channel.attr(ChatWebSocketHandler.USER_ID_KEY)).thenReturn(userIdAttr);
        when(userIdAttr.get()).thenReturn("user123");
    }

    // ────────── 正常流程 ──────────

    @Test
    void shouldCallGrpcStreamOnValidRequest() {
        MsgDto msgDto = buildMsgDto("{\"llmId\":\"llm001\",\"msgContent\":\"你好\"}");

        handler.handler(ctx, msgDto);

        // 验证 gRPC 被正确调用
        verify(grpcClient).streamChat(
                eq("user123"), eq("llm001"), eq("你好"),
                any(), any(), any()  // onToken / onComplete / onError
        );
    }

    @Test
    void shouldSendTokenToClient() {
        // 捕获 gRPC 的 onToken 回调
        ArgumentCaptor<Consumer<AiChatProto.ChatResponse>> onTokenCaptor = ArgumentCaptor.forClass(Consumer.class);
        MsgDto msgDto = buildMsgDto("{\"llmId\":\"llm001\",\"msgContent\":\"hello\"}");

        handler.handler(ctx, msgDto);
        verify(grpcClient).streamChat(anyString(), anyString(), anyString(), onTokenCaptor.capture(), any(), any());

        // 模拟 Python 发来一个 token
        AiChatProto.ChatResponse fakeResponse = AiChatProto.ChatResponse.newBuilder()
                .setContent("你")
                .setBlockType("text")
                .setIsBlockStart(true)
                .setIsBlockEnd(false)
                .setSequence(1)
                .setIsFinal(false)
                .build();

        onTokenCaptor.getValue().accept(fakeResponse);

        // 验证 ctx.writeAndFlush 被调用，且包含正确的 JSON
        ArgumentCaptor<ChatProtocol.Message> msgCaptor = ArgumentCaptor.forClass(ChatProtocol.Message.class);
        verify(ctx, atLeastOnce()).writeAndFlush(msgCaptor.capture());

        ChatProtocol.Message sent = msgCaptor.getValue();
        assertEquals(1108, sent.getType());

        Map<String, Object> token = JSON.parseObject(sent.getExtend(), Map.class);
        assertEquals("你", token.get("content"));
        assertEquals("text", token.get("blockType"));
        assertFalse((Boolean) token.get("isFinal"));
    }

    @Test
    void shouldSendFinalTokenWithEmotion() {
        ArgumentCaptor<Consumer<AiChatProto.ChatResponse>> onTokenCaptor = ArgumentCaptor.forClass(Consumer.class);
        MsgDto msgDto = buildMsgDto("{\"llmId\":\"llm001\",\"msgContent\":\"hi\"}");

        handler.handler(ctx, msgDto);
        verify(grpcClient).streamChat(anyString(), anyString(), anyString(), onTokenCaptor.capture(), any(), any());

        // 模拟最终包
        AiChatProto.ChatResponse finalResponse = AiChatProto.ChatResponse.newBuilder()
                .setContent("")
                .setBlockType("text")
                .setIsFinal(true)
                .setEmotion("happy")
                .setSequence(42)
                .build();

        onTokenCaptor.getValue().accept(finalResponse);

        ArgumentCaptor<ChatProtocol.Message> msgCaptor = ArgumentCaptor.forClass(ChatProtocol.Message.class);
        verify(ctx, atLeastOnce()).writeAndFlush(msgCaptor.capture());

        ChatProtocol.Message sent = msgCaptor.getValue();
        Map<String, Object> token = JSON.parseObject(sent.getExtend(), Map.class);
        assertTrue((Boolean) token.get("isFinal"));
        assertEquals("happy", token.get("emotion"));
    }

    // ────────── 错误处理 ──────────

    @Test
    void shouldSendErrorOnInvalidJson() {
        MsgDto msgDto = buildMsgDto("not-valid-json{{{");

        handler.handler(ctx, msgDto);

        // 不应该调 gRPC
        verify(grpcClient, never()).streamChat(anyString(), anyString(), anyString(), any(), any(), any());

        // 应该发错误消息
        ArgumentCaptor<ChatProtocol.Message> msgCaptor = ArgumentCaptor.forClass(ChatProtocol.Message.class);
        verify(ctx).writeAndFlush(msgCaptor.capture());

        ChatProtocol.Message sent = msgCaptor.getValue();
        assertEquals(1108, sent.getType());
        assertTrue(sent.getExtend().contains("error"));
        assertTrue(sent.getExtend().contains("请求格式错误"));
    }

    @Test
    void shouldSendErrorOnMissingLlmId() {
        MsgDto msgDto = buildMsgDto("{\"msgContent\":\"hello\"}");  // 缺 llmId

        handler.handler(ctx, msgDto);

        verify(grpcClient, never()).streamChat(anyString(), anyString(), anyString(), any(), any(), any());

        ArgumentCaptor<ChatProtocol.Message> msgCaptor = ArgumentCaptor.forClass(ChatProtocol.Message.class);
        verify(ctx).writeAndFlush(msgCaptor.capture());

        assertTrue(msgCaptor.getValue().getExtend().contains("缺少llmId或msgContent"));
    }

    @Test
    void shouldSendErrorOnMissingMsgContent() {
        MsgDto msgDto = buildMsgDto("{\"llmId\":\"llm001\"}");  // 缺 msgContent

        handler.handler(ctx, msgDto);

        verify(grpcClient, never()).streamChat(anyString(), anyString(), anyString(), any(), any(), any());
        verify(ctx).writeAndFlush(argThat((ChatProtocol.Message msg) ->
                msg.getExtend().contains("缺少llmId或msgContent")));
    }

    @Test
    void shouldSendErrorOnGrpcFailure() {
        // 捕获 onError 回调
        ArgumentCaptor<Consumer<Throwable>> onErrorCaptor = ArgumentCaptor.forClass(Consumer.class);
        MsgDto msgDto = buildMsgDto("{\"llmId\":\"llm001\",\"msgContent\":\"hello\"}");

        handler.handler(ctx, msgDto);
        verify(grpcClient).streamChat(anyString(), anyString(), anyString(), any(), any(), onErrorCaptor.capture());

        // 模拟 gRPC 报错
        onErrorCaptor.getValue().accept(new RuntimeException("gRPC 连接被拒绝"));

        ArgumentCaptor<ChatProtocol.Message> msgCaptor = ArgumentCaptor.forClass(ChatProtocol.Message.class);
        verify(ctx, atLeastOnce()).writeAndFlush(msgCaptor.capture());

        ChatProtocol.Message sent = msgCaptor.getValue();
        assertTrue(sent.getExtend().contains("error"));
        assertTrue(sent.getExtend().contains("gRPC 连接被拒绝"));
    }

    // ────────── MsgType 注册 ──────────

    @Test
    void shouldReturnStreamTokenMsgType() {
        assertEquals(MsgTypeConstant.STREAM_TOKEN, handler.getMsgType());
        assertEquals(1108, handler.getMsgType().getCode());
    }

    // ────────── 辅助方法 ──────────

    private MsgDto buildMsgDto(String extend) {
        MsgDto msgDto = new MsgDto();
        msgDto.setType(MsgTypeConstant.STREAM_TOKEN.getCode());
        msgDto.setExtend(extend);
        return msgDto;
    }
}

package com.bedfox.pojo.proto.ai;

import static io.grpc.MethodDescriptor.generateFullMethodName;

/**
 */
@javax.annotation.Generated(
    value = "by gRPC proto compiler (version 1.68.1)",
    comments = "Source: ai_chat.proto")
@io.grpc.stub.annotations.GrpcGenerated
public final class AIChatServiceGrpc {

  private AIChatServiceGrpc() {}

  public static final java.lang.String SERVICE_NAME = "foxchat.ai.AIChatService";

  // Static method descriptors that strictly reflect the proto.
  private static volatile io.grpc.MethodDescriptor<AiChatProto.ChatRequest,
      AiChatProto.ChatResponse> getChatMethod;

  @io.grpc.stub.annotations.RpcMethod(
      fullMethodName = SERVICE_NAME + '/' + "Chat",
      requestType = AiChatProto.ChatRequest.class,
      responseType = AiChatProto.ChatResponse.class,
      methodType = io.grpc.MethodDescriptor.MethodType.SERVER_STREAMING)
  public static io.grpc.MethodDescriptor<AiChatProto.ChatRequest,
      AiChatProto.ChatResponse> getChatMethod() {
    io.grpc.MethodDescriptor<AiChatProto.ChatRequest, AiChatProto.ChatResponse> getChatMethod;
    if ((getChatMethod = AIChatServiceGrpc.getChatMethod) == null) {
      synchronized (AIChatServiceGrpc.class) {
        if ((getChatMethod = AIChatServiceGrpc.getChatMethod) == null) {
          AIChatServiceGrpc.getChatMethod = getChatMethod =
              io.grpc.MethodDescriptor.<AiChatProto.ChatRequest, AiChatProto.ChatResponse>newBuilder()
              .setType(io.grpc.MethodDescriptor.MethodType.SERVER_STREAMING)
              .setFullMethodName(generateFullMethodName(SERVICE_NAME, "Chat"))
              .setSampledToLocalTracing(true)
              .setRequestMarshaller(io.grpc.protobuf.ProtoUtils.marshaller(
                  AiChatProto.ChatRequest.getDefaultInstance()))
              .setResponseMarshaller(io.grpc.protobuf.ProtoUtils.marshaller(
                  AiChatProto.ChatResponse.getDefaultInstance()))
              .setSchemaDescriptor(new AIChatServiceMethodDescriptorSupplier("Chat"))
              .build();
        }
      }
    }
    return getChatMethod;
  }

  private static volatile io.grpc.MethodDescriptor<AiChatProto.DeleteRequest,
      AiChatProto.DeleteResponse> getDeleteMemoryMethod;

  @io.grpc.stub.annotations.RpcMethod(
      fullMethodName = SERVICE_NAME + '/' + "DeleteMemory",
      requestType = AiChatProto.DeleteRequest.class,
      responseType = AiChatProto.DeleteResponse.class,
      methodType = io.grpc.MethodDescriptor.MethodType.UNARY)
  public static io.grpc.MethodDescriptor<AiChatProto.DeleteRequest,
      AiChatProto.DeleteResponse> getDeleteMemoryMethod() {
    io.grpc.MethodDescriptor<AiChatProto.DeleteRequest, AiChatProto.DeleteResponse> getDeleteMemoryMethod;
    if ((getDeleteMemoryMethod = AIChatServiceGrpc.getDeleteMemoryMethod) == null) {
      synchronized (AIChatServiceGrpc.class) {
        if ((getDeleteMemoryMethod = AIChatServiceGrpc.getDeleteMemoryMethod) == null) {
          AIChatServiceGrpc.getDeleteMemoryMethod = getDeleteMemoryMethod =
              io.grpc.MethodDescriptor.<AiChatProto.DeleteRequest, AiChatProto.DeleteResponse>newBuilder()
              .setType(io.grpc.MethodDescriptor.MethodType.UNARY)
              .setFullMethodName(generateFullMethodName(SERVICE_NAME, "DeleteMemory"))
              .setSampledToLocalTracing(true)
              .setRequestMarshaller(io.grpc.protobuf.ProtoUtils.marshaller(
                  AiChatProto.DeleteRequest.getDefaultInstance()))
              .setResponseMarshaller(io.grpc.protobuf.ProtoUtils.marshaller(
                  AiChatProto.DeleteResponse.getDefaultInstance()))
              .setSchemaDescriptor(new AIChatServiceMethodDescriptorSupplier("DeleteMemory"))
              .build();
        }
      }
    }
    return getDeleteMemoryMethod;
  }

  /**
   * Creates a new async stub that supports all call types for the service
   */
  public static AIChatServiceStub newStub(io.grpc.Channel channel) {
    io.grpc.stub.AbstractStub.StubFactory<AIChatServiceStub> factory =
      new io.grpc.stub.AbstractStub.StubFactory<AIChatServiceStub>() {
        @java.lang.Override
        public AIChatServiceStub newStub(io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
          return new AIChatServiceStub(channel, callOptions);
        }
      };
    return AIChatServiceStub.newStub(factory, channel);
  }

  /**
   * Creates a new blocking-style stub that supports unary and streaming output calls on the service
   */
  public static AIChatServiceBlockingStub newBlockingStub(
      io.grpc.Channel channel) {
    io.grpc.stub.AbstractStub.StubFactory<AIChatServiceBlockingStub> factory =
      new io.grpc.stub.AbstractStub.StubFactory<AIChatServiceBlockingStub>() {
        @java.lang.Override
        public AIChatServiceBlockingStub newStub(io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
          return new AIChatServiceBlockingStub(channel, callOptions);
        }
      };
    return AIChatServiceBlockingStub.newStub(factory, channel);
  }

  /**
   * Creates a new ListenableFuture-style stub that supports unary calls on the service
   */
  public static AIChatServiceFutureStub newFutureStub(
      io.grpc.Channel channel) {
    io.grpc.stub.AbstractStub.StubFactory<AIChatServiceFutureStub> factory =
      new io.grpc.stub.AbstractStub.StubFactory<AIChatServiceFutureStub>() {
        @java.lang.Override
        public AIChatServiceFutureStub newStub(io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
          return new AIChatServiceFutureStub(channel, callOptions);
        }
      };
    return AIChatServiceFutureStub.newStub(factory, channel);
  }

  /**
   */
  public interface AsyncService {

    /**
     * <pre>
     * 核心：服务端流式 RPC
     * Java 发一个 ChatRequest，Python 逐个 StreamToken 推回来
     * </pre>
     */
    default void chat(AiChatProto.ChatRequest request,
                      io.grpc.stub.StreamObserver<AiChatProto.ChatResponse> responseObserver) {
      io.grpc.stub.ServerCalls.asyncUnimplementedUnaryCall(getChatMethod(), responseObserver);
    }

    /**
     * <pre>
     * 非流式：删除记忆（兼容旧接口）
     * </pre>
     */
    default void deleteMemory(AiChatProto.DeleteRequest request,
                              io.grpc.stub.StreamObserver<AiChatProto.DeleteResponse> responseObserver) {
      io.grpc.stub.ServerCalls.asyncUnimplementedUnaryCall(getDeleteMemoryMethod(), responseObserver);
    }
  }

  /**
   * Base class for the server implementation of the service AIChatService.
   */
  public static abstract class AIChatServiceImplBase
      implements io.grpc.BindableService, AsyncService {

    @java.lang.Override public final io.grpc.ServerServiceDefinition bindService() {
      return AIChatServiceGrpc.bindService(this);
    }
  }

  /**
   * A stub to allow clients to do asynchronous rpc calls to service AIChatService.
   */
  public static final class AIChatServiceStub
      extends io.grpc.stub.AbstractAsyncStub<AIChatServiceStub> {
    private AIChatServiceStub(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      super(channel, callOptions);
    }

    @java.lang.Override
    protected AIChatServiceStub build(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      return new AIChatServiceStub(channel, callOptions);
    }

    /**
     * <pre>
     * 核心：服务端流式 RPC
     * Java 发一个 ChatRequest，Python 逐个 StreamToken 推回来
     * </pre>
     */
    public void chat(AiChatProto.ChatRequest request,
                     io.grpc.stub.StreamObserver<AiChatProto.ChatResponse> responseObserver) {
      io.grpc.stub.ClientCalls.asyncServerStreamingCall(
          getChannel().newCall(getChatMethod(), getCallOptions()), request, responseObserver);
    }

    /**
     * <pre>
     * 非流式：删除记忆（兼容旧接口）
     * </pre>
     */
    public void deleteMemory(AiChatProto.DeleteRequest request,
                             io.grpc.stub.StreamObserver<AiChatProto.DeleteResponse> responseObserver) {
      io.grpc.stub.ClientCalls.asyncUnaryCall(
          getChannel().newCall(getDeleteMemoryMethod(), getCallOptions()), request, responseObserver);
    }
  }

  /**
   * A stub to allow clients to do synchronous rpc calls to service AIChatService.
   */
  public static final class AIChatServiceBlockingStub
      extends io.grpc.stub.AbstractBlockingStub<AIChatServiceBlockingStub> {
    private AIChatServiceBlockingStub(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      super(channel, callOptions);
    }

    @java.lang.Override
    protected AIChatServiceBlockingStub build(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      return new AIChatServiceBlockingStub(channel, callOptions);
    }

    /**
     * <pre>
     * 核心：服务端流式 RPC
     * Java 发一个 ChatRequest，Python 逐个 StreamToken 推回来
     * </pre>
     */
    public java.util.Iterator<AiChatProto.ChatResponse> chat(
        AiChatProto.ChatRequest request) {
      return io.grpc.stub.ClientCalls.blockingServerStreamingCall(
          getChannel(), getChatMethod(), getCallOptions(), request);
    }

    /**
     * <pre>
     * 非流式：删除记忆（兼容旧接口）
     * </pre>
     */
    public AiChatProto.DeleteResponse deleteMemory(AiChatProto.DeleteRequest request) {
      return io.grpc.stub.ClientCalls.blockingUnaryCall(
          getChannel(), getDeleteMemoryMethod(), getCallOptions(), request);
    }
  }

  /**
   * A stub to allow clients to do ListenableFuture-style rpc calls to service AIChatService.
   */
  public static final class AIChatServiceFutureStub
      extends io.grpc.stub.AbstractFutureStub<AIChatServiceFutureStub> {
    private AIChatServiceFutureStub(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      super(channel, callOptions);
    }

    @java.lang.Override
    protected AIChatServiceFutureStub build(
        io.grpc.Channel channel, io.grpc.CallOptions callOptions) {
      return new AIChatServiceFutureStub(channel, callOptions);
    }

    /**
     * <pre>
     * 非流式：删除记忆（兼容旧接口）
     * </pre>
     */
    public com.google.common.util.concurrent.ListenableFuture<AiChatProto.DeleteResponse> deleteMemory(
        AiChatProto.DeleteRequest request) {
      return io.grpc.stub.ClientCalls.futureUnaryCall(
          getChannel().newCall(getDeleteMemoryMethod(), getCallOptions()), request);
    }
  }

  private static final int METHODID_CHAT = 0;
  private static final int METHODID_DELETE_MEMORY = 1;

  private static final class MethodHandlers<Req, Resp> implements
      io.grpc.stub.ServerCalls.UnaryMethod<Req, Resp>,
      io.grpc.stub.ServerCalls.ServerStreamingMethod<Req, Resp>,
      io.grpc.stub.ServerCalls.ClientStreamingMethod<Req, Resp>,
      io.grpc.stub.ServerCalls.BidiStreamingMethod<Req, Resp> {
    private final AsyncService serviceImpl;
    private final int methodId;

    MethodHandlers(AsyncService serviceImpl, int methodId) {
      this.serviceImpl = serviceImpl;
      this.methodId = methodId;
    }

    @java.lang.Override
    @java.lang.SuppressWarnings("unchecked")
    public void invoke(Req request, io.grpc.stub.StreamObserver<Resp> responseObserver) {
      switch (methodId) {
        case METHODID_CHAT:
          serviceImpl.chat((AiChatProto.ChatRequest) request,
              (io.grpc.stub.StreamObserver<AiChatProto.ChatResponse>) responseObserver);
          break;
        case METHODID_DELETE_MEMORY:
          serviceImpl.deleteMemory((AiChatProto.DeleteRequest) request,
              (io.grpc.stub.StreamObserver<AiChatProto.DeleteResponse>) responseObserver);
          break;
        default:
          throw new AssertionError();
      }
    }

    @java.lang.Override
    @java.lang.SuppressWarnings("unchecked")
    public io.grpc.stub.StreamObserver<Req> invoke(
        io.grpc.stub.StreamObserver<Resp> responseObserver) {
      switch (methodId) {
        default:
          throw new AssertionError();
      }
    }
  }

  public static final io.grpc.ServerServiceDefinition bindService(AsyncService service) {
    return io.grpc.ServerServiceDefinition.builder(getServiceDescriptor())
        .addMethod(
          getChatMethod(),
          io.grpc.stub.ServerCalls.asyncServerStreamingCall(
            new MethodHandlers<
              AiChatProto.ChatRequest,
              AiChatProto.ChatResponse>(
                service, METHODID_CHAT)))
        .addMethod(
          getDeleteMemoryMethod(),
          io.grpc.stub.ServerCalls.asyncUnaryCall(
            new MethodHandlers<
              AiChatProto.DeleteRequest,
              AiChatProto.DeleteResponse>(
                service, METHODID_DELETE_MEMORY)))
        .build();
  }

  private static abstract class AIChatServiceBaseDescriptorSupplier
      implements io.grpc.protobuf.ProtoFileDescriptorSupplier, io.grpc.protobuf.ProtoServiceDescriptorSupplier {
    AIChatServiceBaseDescriptorSupplier() {}

    @java.lang.Override
    public com.google.protobuf.Descriptors.FileDescriptor getFileDescriptor() {
      return AiChatProto.getDescriptor();
    }

    @java.lang.Override
    public com.google.protobuf.Descriptors.ServiceDescriptor getServiceDescriptor() {
      return getFileDescriptor().findServiceByName("AIChatService");
    }
  }

  private static final class AIChatServiceFileDescriptorSupplier
      extends AIChatServiceBaseDescriptorSupplier {
    AIChatServiceFileDescriptorSupplier() {}
  }

  private static final class AIChatServiceMethodDescriptorSupplier
      extends AIChatServiceBaseDescriptorSupplier
      implements io.grpc.protobuf.ProtoMethodDescriptorSupplier {
    private final java.lang.String methodName;

    AIChatServiceMethodDescriptorSupplier(java.lang.String methodName) {
      this.methodName = methodName;
    }

    @java.lang.Override
    public com.google.protobuf.Descriptors.MethodDescriptor getMethodDescriptor() {
      return getServiceDescriptor().findMethodByName(methodName);
    }
  }

  private static volatile io.grpc.ServiceDescriptor serviceDescriptor;

  public static io.grpc.ServiceDescriptor getServiceDescriptor() {
    io.grpc.ServiceDescriptor result = serviceDescriptor;
    if (result == null) {
      synchronized (AIChatServiceGrpc.class) {
        result = serviceDescriptor;
        if (result == null) {
          serviceDescriptor = result = io.grpc.ServiceDescriptor.newBuilder(SERVICE_NAME)
              .setSchemaDescriptor(new AIChatServiceFileDescriptorSupplier())
              .addMethod(getChatMethod())
              .addMethod(getDeleteMemoryMethod())
              .build();
        }
      }
    }
    return result;
  }
}

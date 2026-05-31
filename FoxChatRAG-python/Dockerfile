# ============================================
# App image: application code only (deps from base)
# ============================================
FROM foxchat-python-base:latest
WORKDIR /app

# Copy application code and proto
COPY main.py .
COPY app/ app/
COPY proto/ proto/

# Compile proto → gRPC Python stubs (grpcio-tools already in base image)
RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=app/grpc \
    --grpc_python_out=app/grpc \
    proto/ai_chat.proto \
    && sed -i 's/import ai_chat_pb2/import app.grpc.foxchat.proto.ai.ai_chat_pb2 as ai_chat_pb2/' \
       app/grpc/foxchat/proto/ai/ai_chat_pb2_grpc.py \
    && echo "Proto stubs generated"

EXPOSE 8000
EXPOSE 50051

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

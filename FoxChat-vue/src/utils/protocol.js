import { encodeMessage, decodeMessage } from '@/proto/chat.js';

// 协议常量定义
const ProtocolConstant = {
  MAGIC_NUMBER: 0xCAFEBABE,
  VERSION: 1,
  SERIAL: 1
};

/**
 * 编码器：将 Protocol Message 对象包装成二进制协议帧
 * 协议结构：
 * 4b - Magic Number
 * 1b - Version
 * 1b - Serialization
 * 2b - MsgType
 * 4b - Data Length
 * 4b - Reserved
 * Body - Protobuf Bytes
 */
export function encodeProtocol(messageObj) {
  // 1. 将 JS 对象转为 Protobuf 二进制数据
  const protobufBytes = encodeMessage(messageObj);
  const dataLength = protobufBytes.length;

  // 2. 创建 ArrayBuffer (头部 16 字节 + 数据体长度)
  const buffer = new ArrayBuffer(16 + dataLength);
  const view = new DataView(buffer);
  const uint8View = new Uint8Array(buffer);

  // 3. 写入协议头
  // 注意：Java Netty 默认使用 Big-Endian (网络字节序)
  // DataView.setInt32(byteOffset, value, littleEndian)
  // 第三个参数不传默认是 false (Big-Endian)，显式设为 false 更保险
  view.setInt32(0, ProtocolConstant.MAGIC_NUMBER, false); // Magic Number (4b)
  view.setInt8(4, ProtocolConstant.VERSION);              // Version (1b) - 单字节无端序之分
  view.setInt8(5, ProtocolConstant.SERIAL);               // Serialization (1b)
  view.setInt16(6, messageObj.type, false);               // MsgType (2b)
  view.setInt32(8, dataLength, false);                    // Data Length (4b)
  view.setInt32(12, 0, false);                            // Reserved (4b)

  // 4. 写入 Protobuf 数据体
  uint8View.set(protobufBytes, 16); // 从第 16 字节开始写入

  // Debug: 打印协议头 hex
  const headerHex = Array.from(new Uint8Array(buffer, 0, 16))
    .map(b => b.toString(16).padStart(2, '0').toUpperCase())
    .join(' ');
  console.log(`[Protocol Encode] Length: ${dataLength}, Header: ${headerHex}`);

  return buffer;
}

/**
 * 解码器：将二进制协议帧解析为 JS 对象
 */
export function decodeProtocol(arrayBuffer) {
  const view = new DataView(arrayBuffer);

  // 1. 基础校验 (长度至少 16 字节)
  if (arrayBuffer.byteLength < 16) {
    console.error('收到非法数据包：长度不足 16 字节');
    return null;
  }

  // 2. 校验 Magic Number
  const magicNumber = view.getInt32(0);
  
  if (magicNumber !== ProtocolConstant.MAGIC_NUMBER && magicNumber !== -889275714) {
    console.error('收到非法数据包：Magic Number 不匹配', magicNumber);
    return null;
  }

  // 3. 读取头部信息
  // const version = view.getInt8(4);
  // const serial = view.getInt8(5);
  const type = view.getInt16(6);
  const dataLength = view.getInt32(8);
  // const reserved = view.getInt32(12);

  // 4. 校验数据体长度
  if (arrayBuffer.byteLength < 16 + dataLength) {
    console.error('收到数据包不完整：声明长度', dataLength, '实际剩余', arrayBuffer.byteLength - 16);
    return null;
  }

  // 5. 提取 Protobuf 二进制数据并解码
  // 注意：DataView 的 buffer 可能是整个 WebSocket 的 ArrayBuffer，需要用 offset 切片
  // slice(start, end) 创建一个新的 ArrayBuffer 副本，避免 Uint8Array 偏移问题
  
  const protobufBytes = new Uint8Array(arrayBuffer.slice(16, 16 + dataLength));
  
  try {
    const message = decodeMessage(protobufBytes);
    // 确保 type 字段存在（如果 protobuf 里没解出来，用头部的 type 补上）
    if (!message.type) {
      message.type = type;
    }
    return message;
  } catch (e) {
    console.error('Protobuf 解码失败:', e);
    return null;
  }
}

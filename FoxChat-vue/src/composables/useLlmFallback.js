/**
 * LLM REST 降级函数（gRPC 流失败时自动回退到 Python LangGraph REST）
 *
 * 2026-05-21: 降级目标从 Java /llm/chat 迁移到 Python /chat/msg（同一张 LangGraph）
 *
 * 用法：在 sendMessage 的 onError 回调中调用
 */
import request from '@/utils/request';

export async function fallbackLlmRest(llmId, msgContent, currentFriend, friendList, messageList) {
  const requestFriendId = llmId;

  try {
    // 调用 Python /chat/msg（LangGraph 非流式，逻辑与流式完全一致）
    const res = await request.post('/chat/msg', {
      userId: llmId,
      llmId,
      msgContent
    }, { silent: true, timeout: 120000 });

    let replyBlocks = null;
    let replyEmotion = null;

    // Python /chat/msg 响应格式: { msgId, data: { blocks, emotion } }
    const data = res?.data;
    if (data && data.blocks) {
      replyBlocks = data.blocks.map(block => ({
        type: block.type || 'text',
        text: block.text || '',
        action: block.action || null,
      }));
      replyEmotion = data.emotion;
    }

    // 兼容其他可能的响应格式
    if (!replyBlocks) {
      if (Array.isArray(res)) {
        replyBlocks = res;
      } else if (typeof res === 'string') {
        replyBlocks = [{ type: 'text', text: res }];
      } else {
        replyBlocks = [{ type: 'text', text: JSON.stringify(res) }];
      }
    }

    if (currentFriend.value && (currentFriend.value.userId || currentFriend.value.id) === requestFriendId) {
      const { snowflake } = await import('@/utils/snowflake');
      messageList.value.push({
        id: snowflake.nextId(),
        content: null,
        blocks: replyBlocks || [{ type: 'text', text: '...' }],
        emotion: replyEmotion,
        isMine: false,
        type: 'text',
        createTime: new Date().toISOString(),
        senderId: llmId,
        senderName: currentFriend.value.nickname || currentFriend.value.username,
        senderAvatar: '',
      });

      if (replyEmotion) {
        currentFriend.value.emotion = replyEmotion;
        const friend = friendList.value.find(f => String(f.userId || f.id) === String(requestFriendId));
        if (friend) friend.emotion = replyEmotion;
      }
    }
  } catch (error) {
    console.error('[REST 降级] 也失败了:', error);
    messageList.value.push({
      id: 'failed-' + Date.now(),
      content: '回复失败，点击重试',
      status: 'failed',
      msgContent,
      llmId,
      isMine: false,
      createTime: new Date().toISOString(),
    });
  }
}

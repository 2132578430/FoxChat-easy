/**
 * LLM REST 降级函数（SSE 流失败时自动回退）
 *
 * 用法：在 sendMessage 的 onError 回调中调用
 */
import request from '@/utils/request';

export async function fallbackLlmRest(llmId, msgContent, currentFriend, friendList, messageList, placeholderId = null) {
  const requestFriendId = llmId;

  try {
    const res = await request.post('/llm/chat', {
      llmId,
      msgContent
    }, { silent: true, timeout: 120000 });

    let actualResponse = res;
    if (res && res.code === 1000 && res.data) {
      actualResponse = res.data;
    }

    let replyBlocks = null;
    let replyEmotion = null;

    if (Array.isArray(actualResponse)) {
      const aiMsg = actualResponse.find(m => m.isHuman === false);
      if (aiMsg && aiMsg.msgContent) {
        try {
          const parsed = JSON.parse(aiMsg.msgContent);
          replyBlocks = parsed.blocks || (Array.isArray(parsed) ? parsed : [{ type: 'text', text: aiMsg.msgContent }]);
          replyEmotion = parsed.emotion;
        } catch (e) {
          replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
        }
      }
    } else if (actualResponse && actualResponse.msgId && actualResponse.data) {
      const innerData = actualResponse.data;
      if (Array.isArray(innerData)) {
        const aiMsg = innerData.find(m => m.isHuman === false);
        if (aiMsg && aiMsg.msgContent) {
          try {
            const parsed = JSON.parse(aiMsg.msgContent);
            replyBlocks = parsed.blocks || (Array.isArray(parsed) ? parsed : [{ type: 'text', text: aiMsg.msgContent }]);
            replyEmotion = parsed.emotion;
          } catch (e) {
            replyBlocks = [{ type: 'text', text: aiMsg.msgContent }];
          }
        }
      }
    } else if (typeof actualResponse === 'string') {
      replyBlocks = [{ type: 'text', text: actualResponse }];
    } else {
      replyBlocks = [{ type: 'text', text: JSON.stringify(actualResponse) }];
    }

    if (!replyBlocks) {
      replyBlocks = [{ type: 'text', text: '...' }];
    }

    if (placeholderId) {
      // ── 原地更新流式占位（不删不建，避免 UI 闪动 + "○" 残留）──
      const idx = messageList.value.findIndex(m => m.id === placeholderId);
      if (idx >= 0) {
        messageList.value[idx].blocks = replyBlocks;
        messageList.value[idx].emotion = replyEmotion;
        messageList.value[idx].isStreaming = false;
      }
    } else {
      // ── 新建消息（无流式占位时使用）──
      const { snowflake } = await import('@/utils/snowflake');
      messageList.value.push({
        id: snowflake.nextId(),
        content: null,
        blocks: replyBlocks,
        emotion: replyEmotion,
        isMine: false,
        type: 'text',
        createTime: new Date().toISOString(),
        senderId: llmId,
        senderName: currentFriend.value.nickname || currentFriend.value.username,
        senderAvatar: '',
      });
    }

    if (currentFriend.value && (currentFriend.value.userId || currentFriend.value.id) === requestFriendId) {
      if (replyEmotion) {
        currentFriend.value.emotion = replyEmotion;
        const friend = friendList.value.find(f => String(f.userId || f.id) === String(requestFriendId));
        if (friend) friend.emotion = replyEmotion;
      }
    }
  } catch (error) {
    console.error('[REST 降级] 也失败了:', error);
    if (placeholderId) {
      // 更新占位为失败状态
      const idx = messageList.value.findIndex(m => m.id === placeholderId);
      if (idx >= 0) {
        messageList.value[idx].status = 'failed';
        messageList.value[idx].msgContent = msgContent;
        messageList.value[idx].llmId = llmId;
        messageList.value[idx].isStreaming = false;
        messageList.value[idx].blocks = [{ type: 'text', text: '回复失败，点击重试' }];
      }
    } else {
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
}

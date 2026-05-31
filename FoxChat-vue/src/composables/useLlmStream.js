/**
 * LLM 流式聊天 Composable (SSE)
 *
 * ── 使用方式 ──────────────────────────────────────
 *
 * 在 Home.vue 的 <script setup> 中：
 *
 *   import { useLlmStream } from '@/composables/useLlmStream';
 *   const { sendStreamMessage, isStreaming } = useLlmStream();
 *
 * ── Home.vue 集成 diff ──────────────────────────
 *
 * 找到 sendLlmMessage 函数（约1749行）的这段代码：
 *
 *   const res = await request.post('/llm/chat', {
 *     llmId: llmId,
 *     msgContent: msgContent
 *   }, {
 *     silent: true,
 *     timeout: 120000
 *   });
 *
 * 替换为：
 *
 *   // 先插入用户消息气泡...
 *   // 再插入空的AI占位气泡，拿到 aiMsgIndex
 *   const aiMsgIndex = messages.value.length;
 *   messages.value.push({ type: 'ai', blocks: [{ type: 'text', text: '' }], emotion: null });
 *
 *   let replyBlocks = [{ type: 'text', text: '' }];
 *   let replyEmotion = null;
 *   let currentBlockType = 'text';
 *
 *   await sendStreamMessage(llmId, msgContent, {
 *     onToken: (token, blockType) => {
 *       // 块类型切换 → 可能需要新 block
 *       if (blockType !== currentBlockType && blockType === 'action') {
 *         replyBlocks.push({ type: 'action', action: token, text: null });
 *         currentBlockType = blockType;
 *       } else if (blockType === 'text') {
 *         // 追加到最后一个 text block
 *         const lastBlock = replyBlocks[replyBlocks.length - 1];
 *         if (!lastBlock || lastBlock.type !== 'text') {
 *           replyBlocks.push({ type: 'text', text: token });
 *         } else {
 *           lastBlock.text += token;
 *         }
 *         currentBlockType = blockType;
 *       }
 *       // 实时更新消息列表
 *       messages.value[aiMsgIndex].blocks = [...replyBlocks];
 *     },
 *     onEmotion: (emotion) => {
 *       replyEmotion = emotion;
 *       messages.value[aiMsgIndex].emotion = emotion;
 *     },
 *     onDone: (fullText) => {
 *       // 标记完成，保存到消息历史
 *       messages.value[aiMsgIndex].isComplete = true;
 *       isLlmTyping.value = false;
 *     },
 *     onError: (err) => {
 *       // 降级：回退到旧的 REST 调用
 *       console.warn('SSE流失败，降级REST:', err);
 *       // ... 调用原有的 request.post('/llm/chat', ...) 逻辑
 *     },
 *   });
 *
 * ── 渐进式开关（推荐）────────────────────────────
 *
 * 先加个 feature flag，方便灰度：
 *
 *   const USE_LLM_STREAM = true;  // false 则走旧 REST 路径
 *
 *   if (USE_LLM_STREAM) {
 *     // 走 SSE 流式
 *   } else {
 *     // 走旧 REST（原有代码不动）
 *   }
 */

import { ref } from 'vue';

export function useLlmStream() {
  const isStreaming = ref(false);
  let abortController = null;

  async function sendStreamMessage(llmId, msgContent, callbacks = {}) {
    const { onToken, onBlocks, onEmotion, onDone, onError } = callbacks;

    isStreaming.value = true;
    abortController = new AbortController();

    // 收集完整文本（用于降级时的 full 事件和 onDone）
    let fullText = '';

    try {
      const response = await fetch('/api/llm/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ llmId, msgContent }),
        signal: abortController.signal,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE 协议: event:xxx\ndata:xxx\n\n
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 最后一个可能不完整，保留

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            handleEvent(currentEvent, data);
            currentEvent = '';
          }
          // 空行分隔，忽略
        }
      }

      // 处理残留 buffer
      if (buffer.trim()) {
        // 可能有不完整的最后一行，忽略
      }

    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('[LLM Stream] 错误:', err);
        onError?.(err);
      }
    } finally {
      isStreaming.value = false;
      abortController = null;
    }

    function handleEvent(event, data) {
      switch (event) {
        case 'blocks': {
          // 新格式: [{"type":"action","content":"红光持续"},{"type":"text","content":"你好"}]
          try {
            const blocks = JSON.parse(data);
            onBlocks?.(blocks);
          } catch {
            // 解析失败，回退到旧格式
            onToken?.(data, 'text');
          }
          break;
        }
        case 'token': {
          // 旧格式: "token_text|block_type"（兼容）
          const sepIdx = data.lastIndexOf('|');
          const token = sepIdx >= 0 ? data.slice(0, sepIdx) : data;
          const blockType = sepIdx >= 0 ? data.slice(sepIdx + 1) : 'text';
          fullText += token;
          onToken?.(token, blockType);
          break;
        }
        case 'emotion':
          onEmotion?.(data);
          break;
        case 'full':
          // 降级：整段推送
          fullText = data;
          onToken?.(data, 'text');
          // fall through to done
        case 'done': {
          // 新格式: {"blocks":[...],"emotion":"..."}
          try {
            const result = JSON.parse(data);
            if (result.blocks) {
              onBlocks?.(result.blocks);
            }
            if (result.emotion) {
              onEmotion?.(result.emotion);
            }
            onDone?.(result);
          } catch {
            // 旧格式: 纯文本
            onDone?.(data || fullText);
          }
          break;
        }
      }
    }
  }

  function cancel() {
    if (abortController) {
      abortController.abort();
    }
  }

  return { sendStreamMessage, cancel, isStreaming };
}

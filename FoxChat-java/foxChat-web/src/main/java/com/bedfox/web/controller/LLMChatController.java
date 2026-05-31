package com.bedfox.web.controller;

import com.bedfox.pojo.dto.AddLlmFriendDto;
import com.bedfox.pojo.dto.LlmFriendUpdateDto;
import com.bedfox.pojo.dto.LlmMsgHistoryReqDto;
import com.bedfox.service.service.LlmChatMsgService;
import com.bedfox.service.service.LlmChatService;
import com.bedfox.service.service.LlmMemoryService;
import com.bedfox.service.service.LlmUserService;
import com.bedfox.service.service.LlmConfigService;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.R;
import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.pojo.vo.LlmChatMsgVo;
import com.bedfox.pojo.vo.LlmMemoryVo;
import com.bedfox.pojo.vo.LlmMsgHistoryVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

/**
 * @author bedFox
 * @date 2026/3/19 21:00
 */
@Slf4j
@RestController
@RequestMapping("/llm")
public class LLMChatController {

    @Resource
    LlmUserService llmUserService;

    @Resource
    LlmChatService llmChatService;

    @Resource
    LlmChatMsgService llmChatMsgService;

    @Resource
    LlmConfigService llmConfigService;

    @Resource
    LlmMemoryService llmMemoryService;

    @PostMapping("/chat")
    public R<LlmChatMsgVo> llmChat(@RequestBody Map<String, Object> requestMap) {
        String llmId = (String) requestMap.get("llmId");
        String msgContent = (String) requestMap.get("msgContent");
        String userId = LoginUserHolder.getUserId();

        // 验证配置完整性
        boolean isValid = llmConfigService.validateConfigCount(llmId);
        if (!isValid) {
            log.warn("【聊天请求】llmId={}, 配置不完整", llmId);
            return R.error(ResultStatusConstant.LLM_CONFIG_INCOMPLETE_EXCEPTION);
        }

        LlmChatMsgVo chatMsgVo = llmChatService.llmChat(llmId, msgContent, userId);
        return R.ok(chatMsgVo);
    }

    /**
     * 流式聊天（SSE）
     * 前端通过 EventSource 或 fetch + ReadableStream 连接此端点，
     * 接收逐 token 的 AI 回复。
     *
     * SSE 事件：
     *   event: token   data: <token>|<block_type>   -- 增量文本
     *   event: emotion data: <emotion_label>         -- 情感标签
     *   event: done    data: ""                      -- 流结束
     *   event: full    data: <full_response>         -- 降级时整段推送
     */
    @PostMapping("/stream")
    public SseEmitter llmChatStream(@RequestBody Map<String, Object> requestMap) {
        String llmId = (String) requestMap.get("llmId");
        String msgContent = (String) requestMap.get("msgContent");
        String userId = LoginUserHolder.getUserId();

        // 验证配置完整性
        boolean isValid = llmConfigService.validateConfigCount(llmId);
        if (!isValid) {
            log.warn("【流式请求】llmId={}, 配置不完整", llmId);
            SseEmitter errorEmitter = new SseEmitter();
            errorEmitter.completeWithError(
                new RuntimeException("LLM配置不完整，请前往设置页面配置")
            );
            return errorEmitter;
        }

        log.info("[SSE Stream] llmId={}, msg={}", llmId, msgContent.substring(0, Math.min(30, msgContent.length())));
        return llmChatService.llmChatStream(llmId, msgContent, userId);
    }

    /**
     * 获取模型记忆面板数据（角色卡+锚点+画像+记忆银行）
     */
    @GetMapping("/{llmId}/memory")
    public R<LlmMemoryVo> getMemory(@PathVariable String llmId) {
        LlmMemoryVo vo = llmMemoryService.getMemory(llmId);
        return R.ok(vo);
    }

    @PostMapping("/add")
    public R<String> addLlm(@RequestBody AddLlmFriendDto friendDto) {
        String llmId = llmUserService.saveFriend(friendDto);
        return R.ok(llmId);
    }

    @PostMapping("/history")
    public R<List<LlmMsgHistoryVo>> getMsgHistory(@RequestBody LlmMsgHistoryReqDto reqDto) {
        List<LlmMsgHistoryVo> list = llmChatMsgService.getMsgHistory(
            LoginUserHolder.getUserId(),
            reqDto.getLlmId(),
            reqDto.getLastTime(),
            reqDto.getLastId()
        );

        return R.ok(list);
    }

    @PostMapping("/update")
    public R<Void> updateLlmFriend(@RequestBody LlmFriendUpdateDto updateDto) {
        llmUserService.updateFriend(updateDto);
        return R.ok();
    }

    /**
     * 模型头像上传接口
     */
    @PostMapping("/uploadAvatar")
    public R<String> uploadAvatar(@RequestParam("file") MultipartFile file) {
        String fileUrl = llmUserService.uploadAvatar(file);
        return R.ok(fileUrl);
    }

    /**
     * 激活创造物
     * @param llmId 创造物ID
     * @return 激活结果，配置不完整时返回缺失场景列表
     */
    @PostMapping("/activate/{llmId}")
    public R<Map<String, Object>> activateLlm(@PathVariable String llmId) {
        Map<String, Object> result = llmUserService.activateLlm(llmId);

        Boolean success = (Boolean) result.get("success");
        if (Boolean.TRUE.equals(success)) {
            return R.ok();
        }

        ResultStatusConstant error = (ResultStatusConstant) result.get("error");
        if (result.containsKey("missingScenarios")) {
            return R.error(error, result);
        }
        return R.error(error);
    }
}

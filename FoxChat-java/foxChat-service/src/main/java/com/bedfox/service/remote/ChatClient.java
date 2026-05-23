package com.bedfox.service.remote;

import com.bedfox.pojo.to.ChatMsgTo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Map;

/**
 * @author bedFox
 * @date 2026/3/22 21:07
 */

@Component
@FeignClient(name = "chat-service", url = "${remote.python-url}")
public interface ChatClient {
    @PostMapping("/chat/msg")
    String chatMsg(ChatMsgTo chatMsgTo);

    @PostMapping("/chat/superMsg")
    String superChatMsg(ChatMsgTo chatMsgTo);

    @PostMapping("/chat/delete")
    void deleteMsg(@RequestParam("userId") String userId, @RequestParam("llmId") String llmId);

    @PostMapping("/llm/testConnection")
    Map<String, Object> testConnection(@RequestBody Map<String, String> request);
}

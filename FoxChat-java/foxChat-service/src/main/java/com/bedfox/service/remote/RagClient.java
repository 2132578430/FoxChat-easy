package com.bedfox.service.remote;

import com.bedfox.pojo.to.RagSearchFileMsgTo;
import com.bedfox.common.util.M;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

/**
 * @author bedFox
 * @date 2026/3/17 16:09
 */
@Component
@FeignClient(name = "rag-service", url = "${remote.python-url}")
public interface RagClient {
    @PostMapping("/rag/searchFile")
    String searchFile(@RequestBody M<RagSearchFileMsgTo> msg);
}

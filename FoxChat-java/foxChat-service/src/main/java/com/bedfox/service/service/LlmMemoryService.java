package com.bedfox.service.service;

import com.bedfox.pojo.vo.LlmMemoryVo;

/**
 * 模型记忆面板 Service
 * @author bedFox
 */
public interface LlmMemoryService {

    /**
     * 获取模型完整记忆数据
     * @param llmId 模型ID
     * @return 记忆面板VO
     */
    LlmMemoryVo getMemory(String llmId);
}

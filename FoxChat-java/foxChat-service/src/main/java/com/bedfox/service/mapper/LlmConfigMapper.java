package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.LlmConfig;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * LLM 配置 Mapper 接口
 */
public interface LlmConfigMapper extends BaseMapper<LlmConfig> {

    /**
     * 根据 llmId 查询所有配置
     */
    List<LlmConfig> selectByLlmId(@Param("llmId") String llmId);

    /**
     * 根据 llmId 和 scenario 查询配置
     */
    LlmConfig selectByLlmIdAndScenario(@Param("llmId") String llmId, @Param("scenario") String scenario);

    /**
     * 批量插入配置
     */
    int insertBatch(@Param("list") List<LlmConfig> configs);

    /**
     * 更新配置
     */
    int updateByLlmIdAndScenario(LlmConfig config);

    /**
     * 删除配置
     */
    int deleteByLlmIdAndScenario(@Param("llmId") String llmId, @Param("scenario") String scenario);

    /**
     * 统计配置数量
     */
    int countByLlmId(@Param("llmId") String llmId);

    /**
     * 根据 llmId 删除所有配置
     */
    int deleteByLlmId(@Param("llmId") String llmId);
}
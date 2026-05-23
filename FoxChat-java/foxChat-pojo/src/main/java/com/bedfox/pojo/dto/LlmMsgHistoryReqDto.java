package com.bedfox.pojo.dto;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class LlmMsgHistoryReqDto {
    private String llmId;
    private Long lastTime;
    private String lastId;
}
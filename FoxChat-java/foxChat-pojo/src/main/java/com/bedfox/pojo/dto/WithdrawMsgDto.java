package com.bedfox.pojo.dto;

import lombok.Data;

import java.util.List;

/**
 * @author bedFox
 */
@Data
public class WithdrawMsgDto {
    private List<String> msgIds;
}

package com.bedfox.web.controller;

import com.bedfox.pojo.dto.HistoryGroupDto;
import com.bedfox.service.service.GroupMsgService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.GroupMsgHistoryVo;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * @author bedFox
 */
@RequestMapping("/groupMsg")
@RestController
public class GroupMsgController {

    @Resource
    GroupMsgService groupMsgService;

    @PostMapping("/history")
    public R<List<GroupMsgHistoryVo>> historyMsg(@RequestBody HistoryGroupDto historyGroupDto){
        List<GroupMsgHistoryVo> list = groupMsgService.historyMsg(historyGroupDto);
        return R.ok(list);
    }
}

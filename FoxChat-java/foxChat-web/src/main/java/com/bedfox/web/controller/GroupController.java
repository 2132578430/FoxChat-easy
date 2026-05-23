package com.bedfox.web.controller;

import com.bedfox.pojo.dto.ApplyGroupDto;
import com.bedfox.pojo.dto.GroupDto;
import com.bedfox.service.service.ChatGroupService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.GroupVo;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * @author bedFox
 */
@RequestMapping("/group")
@RestController
public class GroupController {

    @Resource
    ChatGroupService chatGroupService;

    @PostMapping("/add")
    public R<String> addGroup(@RequestBody GroupDto groupDto) {
        chatGroupService.addGroup(groupDto);
        return R.ok();
    }
    @GetMapping("/search")
    public R<List<GroupVo>> searchGroup(@RequestParam("keyword") String keyword) {
        List<GroupVo> groupList = chatGroupService.searchGroup(keyword);
        return R.ok(groupList);
    }

    @GetMapping("/list")
    public R<List<GroupVo>> listGroup() {
        List<GroupVo> groupList = chatGroupService.listGroup();
        return R.ok(groupList);
    }

    @PostMapping("/join")
    public R<String> applyGroup(@RequestBody ApplyGroupDto applyGroupDto) {
        chatGroupService.applyGroup(applyGroupDto.getGroupId(), applyGroupDto.getReason());
        return R.ok();
    }
}

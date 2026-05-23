package com.bedfox.web.controller;

import com.bedfox.pojo.dto.DeleteMsgDto;
import com.bedfox.pojo.dto.HistoryUserDto;
import com.bedfox.pojo.dto.SignMsgFriendDto;
import com.bedfox.pojo.dto.WithdrawMsgDto;
import com.bedfox.service.service.ChatMsgService;
import com.bedfox.service.service.MsgStatusService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.HistoryMsgVo;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * @author bedFox
 */
@RestController
@RequestMapping("/msg")
public class MsgController {

    @Resource
    ChatMsgService chatMsgService;

    @Resource
    MsgStatusService msgStatusService;

    /**
     * 显示未签收的好友信息
     *
     * @param signMsgFriendDto
     * @return
     */
    @PostMapping("/noSignMsg")
    public R<String> signMsg(@RequestBody SignMsgFriendDto signMsgFriendDto) {
        String msgId = chatMsgService.noSignMsg(signMsgFriendDto.getFriendId());
        return R.ok(msgId);
    }

    /**
     * 查找历史消息记录
     *
     * @param historyUserDto
     * @return
     */
    @PostMapping("/history")
    public R<List<HistoryMsgVo>> msgHistory(@RequestBody HistoryUserDto historyUserDto) {
        List<HistoryMsgVo> historyMsgList = chatMsgService.msgHistory(historyUserDto);
        return R.ok(historyMsgList);
    }

    /**
     * 显示好友未读消息数量
     *
     * @return
     */
    @GetMapping("/unreadCounts")
    public R<Map<String, Long>> unreadCount() {
        Map<String, Long> map = chatMsgService.getUnreadCount();
        return R.ok(map);
    }

    /**
     * 撤回信息
     *
     * @return
     */
    @PostMapping("/withdraw")
    public R<String> withdrawMsg(@RequestBody WithdrawMsgDto withdrawMsgDto) {
        chatMsgService.withdrawMsg(withdrawMsgDto);

        return R.ok();
    }

    @PostMapping("/delete")
    public R<String> deleteMsg(@RequestBody DeleteMsgDto deleteMsgDto) {
        msgStatusService.deleteMsg(deleteMsgDto);

        return R.ok();
    }

}

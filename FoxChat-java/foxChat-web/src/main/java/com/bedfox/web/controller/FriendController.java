package com.bedfox.web.controller;

import com.bedfox.pojo.dto.AddFriendDto;
import com.bedfox.pojo.dto.SearchUserDto;
import com.bedfox.service.service.FriendsRequestService;
import com.bedfox.service.service.FriendsService;
import com.bedfox.service.service.UsersService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.FriendVo;
import com.bedfox.pojo.vo.SearchUserVo;
import com.bedfox.pojo.vo.SelectFriendVo;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * @author bedFox
 */
@RestController
@RequestMapping("/friend")
public class FriendController {

    @Resource
    UsersService usersService;

    @Resource
    FriendsService friendsService;

    @Resource
    FriendsRequestService friendsRequestService;

    /**
     * 搜索好友
     * @param searchUserDto
     * @return
     */
    @PostMapping("/search")
    public R<List<SearchUserVo>> searchFriend(@RequestBody SearchUserDto searchUserDto) {
        List<SearchUserVo> friendList = usersService.searchFriend(searchUserDto);
        return R.ok(friendList);
    }

    /**
     * 查找当前用户的好友申请记录
     * @return
     */
    @GetMapping("/request")
    public R<List<FriendVo>> requestFriendList() {
        List<FriendVo> friendList = friendsRequestService.requestFriendList();
        return R.ok(friendList);
    }

    /**
     * 添加好友
     * @param addFriendDto
     * @return
     */
    @PostMapping("/accept")
    public R<String> addFriend(@RequestBody AddFriendDto addFriendDto) {
        friendsService.addFriend(addFriendDto);
        return R.ok();
    }

    /**
     * 展示好友与llm模型
     * @return
     */
    @GetMapping("/list")
    public R<List<FriendVo>> listFriends() {
        return R.ok(friendsService.listAllFriends());
    }

    /**
     * 选中好友
     * @param friendId
     * @return
     */
    @GetMapping("/history")
    public R<SelectFriendVo> selectFriend(@RequestParam("friendId") String friendId) {
        SelectFriendVo friendVo = usersService.selectUser(friendId);
        return R.ok(friendVo);
    }

    /**
     * 删除好友
     */
    @GetMapping("/delete")
    public R<String> deleteFriend(
            @RequestParam("friendId") String friendId,
            @RequestParam("role") Integer role
    ) {
        friendsService.deleteFriend(friendId, role);
        return R.ok();
    }
}

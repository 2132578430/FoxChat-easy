package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.LlmUser;
import com.bedfox.pojo.dto.AddLlmFriendDto;
import com.bedfox.pojo.dto.LlmFriendUpdateDto;
import com.bedfox.pojo.vo.FriendVo;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
* @author 21325
* @description 针对表【llm_user】的数据库操作Service
* @createDate 2026-03-20 13:26:13
*/
public interface LlmUserService extends IService<LlmUser> {

    // 保存模型好友
    String saveFriend(AddLlmFriendDto friendDto);

    // 请求模型好友列表
    List<FriendVo> friendList(String userId);

    // 删除模型好友
    void deleteFriend(String friendId);

    // 更新模型好友信息
    void updateFriend(LlmFriendUpdateDto updateDto);

    // 上传模型好友头像
    String uploadAvatar(MultipartFile file);
}

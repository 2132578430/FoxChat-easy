package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.common.constant.ChatRoleConstant;
import com.bedfox.common.constant.FileContstant;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.MinioUtil;
import com.bedfox.common.util.MqUtil;
import com.bedfox.pojo.domain.LlmChatMsg;
import com.bedfox.pojo.domain.LlmUser;
import com.bedfox.pojo.dto.AddLlmFriendDto;
import com.bedfox.pojo.dto.LlmFriendUpdateDto;
import com.bedfox.service.mapper.LlmUserMapper;
import com.bedfox.service.remote.ChatClient;
import com.bedfox.service.service.LlmChatMsgService;
import com.bedfox.service.service.LlmUserService;
import com.bedfox.pojo.to.ChatMqMsgTo;
import com.bedfox.pojo.vo.FriendVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

import org.springframework.web.multipart.MultipartFile;


/**
* @author 21325
* @description 针对表【llm_user】的数据库操作Service实现
* @createDate 2026-03-20 13:26:13
*/
@Slf4j
@Service
public class LlmUserServiceImpl extends ServiceImpl<LlmUserMapper, LlmUser>
    implements LlmUserService{

    @Resource
    MqUtil mqUtil;

    @Resource
    MinioUtil minioUtil;

    @Resource
    ChatClient chatClient;

    @Resource
    LlmChatMsgService llmChatMsgService;

    /**
     * 保存大模型
     * @param friendDto
     */
    @Override
    public String saveFriend(AddLlmFriendDto friendDto) {
        String userId = LoginUserHolder.getUserId();
        LlmUser llm = new LlmUser();
        String myName = friendDto.getMyName();
        String partnerName = friendDto.getPartnerName();
        String experience = friendDto.getExperience();

        // 拼接主语信息，降低模型识别错主人的概率
        String fullExperience = "以下为你与我的经历。你应该称呼我为" + myName + "，你的名字是" + partnerName + "。用户描述经历原文：" + experience;

        llm.setLlmName(friendDto.getNickname());
        llm.setMemoryContent(fullExperience);
        llm.setUserId(userId);

        // 保存模型
        save(llm);

        // 将记忆存入rabbitmq，记忆初始化交给python
        ChatMqMsgTo chatMqMsgTo = new ChatMqMsgTo();

        chatMqMsgTo.setUserId(userId);
        chatMqMsgTo.setExperience(fullExperience);
        chatMqMsgTo.setLlmId(llm.getId());

        mqUtil.sendChatMsg(chatMqMsgTo);

        System.out.println(chatMqMsgTo);

        return llm.getId();
    }

    /**
     * 返回用户模型列表给好友检索
     * @return
     */
    @Override
    public List<FriendVo> friendList(String userId) {
        List<LlmUser> llmList = list(new LambdaQueryWrapper<LlmUser>()
                .eq(LlmUser::getUserId, userId));

        return llmList.stream()
                .map(llmUser -> {
                    FriendVo friendVo = new FriendVo();

                    friendVo.setRole(ChatRoleConstant.LLM);
                    friendVo.setOnline(Boolean.TRUE);
                    friendVo.setUsername(llmUser.getLlmName());
                    friendVo.setUserId(llmUser.getId());
                    friendVo.setNickname(llmUser.getLlmName());
                    friendVo.setFaceImage(llmUser.getFaceImage());

                    return friendVo;
                })
                .toList();
    }

    /**
     * 删除llm好友
     * @param llmId
     */
    @Override
    public void deleteFriend(String llmId) {
        String userId = LoginUserHolder.getUserId();

        // 先删除向量库相关信息
        chatClient.deleteMsg(userId, llmId);

        // 删除数据库相关信息
        removeById(llmId);

        llmChatMsgService.remove(new LambdaQueryWrapper<LlmChatMsg>()
                .eq(LlmChatMsg::getLlmId, llmId).eq(LlmChatMsg::getSendUserId, userId));
    }

    /**
     * 更新llm好友信息
     * @param updateDto
     */
    @Override
    public void updateFriend(LlmFriendUpdateDto updateDto) {
        String userId = LoginUserHolder.getUserId();
        LlmUser llmUser = getById(updateDto.getLlmId());
        if (llmUser == null || !llmUser.getUserId().equals(userId)) {
            return;
        }
        llmUser.setLlmName(updateDto.getNickname());
        llmUser.setFaceImage(updateDto.getFaceImage());
        updateById(llmUser);
    }

    /**
     * 上传模型头像
     * @param file 文件
     * @return 文件URL
     */
    @Override
    public String uploadAvatar(MultipartFile file) {
        String userId = LoginUserHolder.getUserId();
        return minioUtil.uploadFile(file, FileContstant.LLM_AVATAR_BIZPATH, userId);
    }
}
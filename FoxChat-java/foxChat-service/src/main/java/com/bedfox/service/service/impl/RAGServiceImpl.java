package com.bedfox.service.service.impl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.bedfox.common.constant.FileContstant;
import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.pojo.domain.RagFile;
import com.bedfox.common.exception.BusinessException;
import com.bedfox.service.remote.RagClient;
import com.bedfox.service.service.RAGService;
import com.bedfox.service.service.RagFileService;
import com.bedfox.pojo.to.RagMqMsgTo;
import com.bedfox.pojo.to.RagSearchFileMsgResTo;
import com.bedfox.pojo.to.RagSearchFileMsgTo;
import com.bedfox.common.util.LoginUserHolder;
import com.bedfox.common.util.M;
import com.bedfox.common.util.MinioUtil;
import com.bedfox.common.util.MqUtil;
import com.bedfox.pojo.vo.RagSearchVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.codec.digest.DigestUtils;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * @author bedFox
 * @description 模型逻辑实现，包含RAG和聊天逻辑
 * @date 2026/3/15 12:21
 */
@Service
@Slf4j
public class RAGServiceImpl implements RAGService {

    @Resource
    RagFileService ragFileService;

    @Resource
    RagClient ragClient;

    @Resource
    MinioUtil minioUtil;

    @Resource
    MqUtil mqUtil;

    /**
     * 将文件存入miniO，并将路径存入数据库，发送信息给mq
     * @param file
     */
    @Override
    public void upload(MultipartFile file) {
        RagFile ragFile = new RagFile();
        String fileName = file.getOriginalFilename();
        String userId = LoginUserHolder.getUserId();

        // 在数据库存数据
        ragFile.setFileName(fileName);
        ragFile.setUserId(userId);
        ragFile.setStatus(FileContstant.NEW_FILE);
        ragFile.setCreateTime(LocalDateTime.now());
        ragFileService.save(ragFile);

        // 将文件上传到MiniO，获取路径
        String filePath = minioUtil.uploadFile(file, FileContstant.RAG_BIZPATH, userId);

        ragFile.setFilePath(filePath);

        // 再更新数据库的路径信息
        ragFile.setStatus(FileContstant.UPLOAD_MINIO);
        ragFileService.updateById(ragFile);

        // 向mq发送文件信息
        RagMqMsgTo msg = new RagMqMsgTo();

        msg.setUserId(userId);
        msg.setFilePath(filePath);

        mqUtil.sendRagUploadMsg(msg);
    }

    /**
     * 将文件上传入rag
     * @param fileList
     */
    @Override
    public void upload(List<MultipartFile> fileList) {
        String userId = LoginUserHolder.getUserId();

        Map<String, String> queryRagFileMap = ragFileService.list(new LambdaQueryWrapper<RagFile>()
                .eq(RagFile::getUserId, userId))
                .stream()
                .collect(Collectors.toMap(RagFile::getFilePath, RagFile::getId));

        // 构建rag列表
        List<RagFile> ragFileList = fileList.stream().map(file -> {
            RagFile ragFile = new RagFile();

            try {
                String fileName = file.getOriginalFilename();

                ragFile.setFileName(fileName);
                ragFile.setUserId(userId);
                ragFile.setStatus(FileContstant.NEW_FILE);
                ragFile.setCreateTime(LocalDateTime.now());

                // 这里计算文件未来将会存入的路径，防止重复导致冲突
                String futureFilePath = minioUtil.getExceptedFilePath(
                        file.getBytes(),
                        FileContstant.RAG_BIZPATH,
                        file.getOriginalFilename(),
                        userId
                );

                // 如果已经存在，就将id赋值，之后直接更新时间
                if (queryRagFileMap.containsKey(futureFilePath)) {
                    ragFile.setId(queryRagFileMap.get(futureFilePath));
                }

                return ragFile;
            } catch (IOException e) {
                throw new BusinessException(ResultStatusConstant.FILE_UPLOAD_ERROR_EXCEPTION);
            }

        }).toList();

        // 在数据库存数据，并填入id
        ragFileService.saveOrUpdateBatch(ragFileList);

        // 将文件上传到MiniO，获取路径
        IntStream.range(0, fileList.size()).parallel().forEach(i -> {
            RagFile ragFile = ragFileList.get(i);
            MultipartFile file = fileList.get(i);

            String filePath = ragFile.getFilePath();
            if (ragFile.getFilePath() == null) {
                filePath = minioUtil.uploadFile(file, FileContstant.RAG_BIZPATH, userId);
            }

            ragFile.setFilePath(filePath);
            ragFile.setStatus(FileContstant.UPLOAD_MINIO);
        });

        // 再更新数据库的路径信息
        ragFileService.saveOrUpdateBatch(ragFileList);

        // 向mq发送文件信息
        ragFileList.stream()
                .filter(r -> r.getFilePath() != null)
                .forEach(ragFile -> {
                    RagMqMsgTo msg = new RagMqMsgTo();

                    msg.setUserId(ragFile.getUserId());
                    msg.setFilePath(ragFile.getFilePath());
                    mqUtil.sendRagUploadMsg(msg);
                });
    }

    /**
     * 显示当前用户存入rag知识库的文件名
     *
     * @return
     */
    @Override
    public List<RagFile> listFile() {
        String userId = LoginUserHolder.getUserId();

        LambdaQueryWrapper<RagFile> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(RagFile::getUserId, userId);

        return ragFileService.list(queryWrapper);
    }

    @Override
    public List<RagSearchVo> searchRagFile(String msg) {
        RagSearchFileMsgTo msgTo = new RagSearchFileMsgTo();
        msgTo.setUserId(LoginUserHolder.getUserId());
        msgTo.setMsg(msg);

        M<RagSearchFileMsgTo> sendMsg = M.getMsg(msgTo);

        String resultJson = ragClient.searchFile(sendMsg);

        M<List<RagSearchFileMsgResTo>> result = JSON
                .parseObject(resultJson, new TypeReference<>() {});

        // 如果内网消息有问题
        if (ResultStatusConstant.RAG_MSG_ERROR_EXCEPTION.getCode().toString().equals((result.getMsgId()))) {
            throw new BusinessException(ResultStatusConstant.RAG_MSG_ERROR_EXCEPTION);
        }

        List<RagSearchFileMsgResTo> dataList = result.getData();

        List<String> filePathList = dataList.stream().map(RagSearchFileMsgResTo::getFilePath).toList();

        // 获取文件本体
        List<RagFile> ragFileList = ragFileService
                .list(new LambdaQueryWrapper<RagFile>().in(RagFile::getFilePath, filePathList));

        // 将文件路径映射到文件名
        Map<String, String> filePathMap = ragFileList.stream()
                .collect(Collectors.toMap(RagFile::getFilePath, RagFile::getFileName));

        return dataList.stream().map(msgResTo -> {
            RagSearchVo ragSearchVo = new RagSearchVo();

            ragSearchVo.setScore(msgResTo.getScore());
            ragSearchVo.setFilePath(msgResTo.getFilePath());
            ragSearchVo.setFileName(filePathMap.get(msgResTo.getFilePath()));

            return ragSearchVo;
        }).toList();
    }

    /**
     * 校验返回的数据是否损失
     * 暂时屏蔽
     *
     * @param result
     * @return
     */
    private boolean examMessage(M<String> result) {
        String data = result.getData();

        String dataJson = JSON.toJSONString(data);

        String examMsgId = DigestUtils.md5Hex(dataJson);

        return examMsgId.equals(result.getMsgId());
    }
}

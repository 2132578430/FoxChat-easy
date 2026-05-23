package com.bedfox.service.task;

import com.bedfox.pojo.domain.RagFile;
import com.bedfox.service.service.RagFileService;
import com.bedfox.common.util.MinioUtil;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 定时任务类
 *
 * @author bedFox
 * @date 2026/3/15 14:25
 */
@Component
@Slf4j
public class RAGTask {

    @Resource
    RagFileService ragFileService;

    @Resource
    MinioUtil minioUtil;

    @Value("${minio.bucket-name}")
    String bucketName;
    /**
     * 每隔3个小时清理数据库中一小时以上的僵尸文件
     */
    @Scheduled(cron = "0 0 */3 * * ?")
    public void cleanZombieFiles() {
        String separator = "/" + bucketName + "/";
        int len = separator.length();

        List<RagFile> files = ragFileService.selectZombieFile();

        if (files != null && !files.isEmpty()) {
            record FileResult(List<String> names, List<String> ids) {}

            // 取出路径和id集合
            FileResult result = files.stream()
                    .filter(file -> file.getFilePath() != null)
                    .collect(Collectors.teeing(
                            Collectors.mapping(file -> {
                                String filePath = file.getFilePath();
                                int index = filePath.indexOf(separator) + len;
                                return filePath.substring(index);
                            }, Collectors.toList()),
                            Collectors.mapping(RagFile::getId, Collectors.toList()),
                            FileResult::new
                    ));

            List<String> fileNameList = result.names();
            List<String> idList = result.ids();

            // 先删除minio
            minioUtil.deleteBatchFileNames(fileNameList);

            // 再删除database
            ragFileService.removeBatchByIds(idList);
        }
    }
}

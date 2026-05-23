package com.bedfox.common.util;

import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.common.exception.BusinessException;
import io.minio.*;
import io.minio.messages.DeleteObject;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.codec.digest.DigestUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * @author bedFox
 */
@Component
@Slf4j
public class MinioUtil {

    @Resource
    MinioClient minioClient;

    @Resource
    ThreadPoolExecutor executor;

    @Value("${minio.bucket-name}")
    String bucketName;
    @Value("${minio.endpoint}")
    String endpoint;
    @Value("${minio.public-endpoint}")
    String publicEndpoint;

    public static DateTimeFormatter format = DateTimeFormatter.ofPattern("yyyy/MM/dd");

    public String uploadFile(MultipartFile file, String bizPath, String owner) {
        try {
            // 找到储存bucket
            BucketExistsArgs bucketExist = BucketExistsArgs.builder().bucket(bucketName).build();
            boolean exist = minioClient.bucketExists(bucketExist);

            if (!exist) {
                // 如果不存在，创建桶
                MakeBucketArgs makeBucketArgs = MakeBucketArgs.builder().bucket(bucketName).build();

                minioClient.makeBucket(makeBucketArgs);

                // 设置桶为可公共读
                String config = getPolicyConfig();

                minioClient.setBucketPolicy(SetBucketPolicyArgs
                        .builder()
                        .bucket(bucketName)
                        .config(config)
                        .build());
            }

            // 根据是否传入文件名判断是否需要创建随机文件名
            byte[] fileData = file.getBytes();
            String fileName = getCerTainFileName(fileData, bizPath, file.getOriginalFilename(), owner);

            // 上传文件
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucketName)
                    .object(fileName)
                    .stream(new java.io.ByteArrayInputStream(fileData), fileData.length, -1)
                    .contentType(file.getContentType())
                    .build());

            // 返回文件路径
            return publicEndpoint + "/" + bucketName + "/" + fileName;
        } catch (Exception e) {
            log.error("文件上传错误:{}", e.getMessage());
            throw new BusinessException(ResultStatusConstant.FILE_UPLOAD_ERROR_EXCEPTION);
        }
    }

    public String getExceptedFilePath(byte[] file, String bizPath, String fileName, String userId) throws IOException{
        return publicEndpoint + "/" + bucketName + "/" + getCerTainFileName(file, bizPath, fileName, userId);
    }

    private String getCerTainFileName(byte[] file, String bizPath, String fileName, String userId) throws IOException {
        String md5 = DigestUtils.md5Hex(file);

        return bizPath + "/" + userId + "/" + md5 + "_" + fileName;
    }

    private String getRandomFileName(MultipartFile file, String bizPath) {
        return bizPath + "/" + LocalDateTime.now().format(format) + "/" + UUID.randomUUID() + file.getOriginalFilename();
    }

    private String getPolicyConfig() {
        return """
                    {
                      "Version": "2012-10-17",
                      "Statement": [
                        {
                          "Effect": "Allow",
                          "Principal": "*",
                          "Action": ["s3:GetObject"],
                          "Resource": ["arn:aws:s3:::%s/*"]
                        }
                      ]
                    }
                    """.formatted(bucketName);
    }

    public void deleteBatchFileNames(List<String> fileList) {
        List<DeleteObject> deleteObjectList = fileList.stream()
                .map(DeleteObject::new)
                .toList();

        minioClient.removeObjects(
                RemoveObjectsArgs
                        .builder()
                        .bucket(bucketName)
                        .objects(deleteObjectList)
                        .build()
        );
    }
}

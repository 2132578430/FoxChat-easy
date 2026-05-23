package com.bedfox.service.service;


import com.bedfox.pojo.domain.RagFile;
import com.bedfox.pojo.vo.RagSearchVo;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * @author bedFox
 * @date 2026/3/15 12:20
 */
public interface RAGService {
    void upload(MultipartFile file);

    void upload(List<MultipartFile> file);

    List<RagFile> listFile();

    List<RagSearchVo> searchRagFile(String msg);
}

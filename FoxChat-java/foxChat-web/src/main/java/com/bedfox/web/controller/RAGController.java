package com.bedfox.web.controller;

import com.bedfox.pojo.domain.RagFile;
import com.bedfox.service.service.RAGService;
import com.bedfox.common.util.R;
import com.bedfox.pojo.vo.RagSearchVo;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * @author bedFox
 * @date 2026/3/14 20:24
 */
@Slf4j
@RestController
@RequestMapping("/rag")
public class RAGController {
    @Resource
    RAGService ragService;

    /**
     * 上传文件进入向量数据库
     * 同时作为RAG知识库一部分
     *
     * @param file
     * @return
     */
    @PostMapping("/uploadVector")
    public R<String> uploadVector(@RequestParam("file")List<MultipartFile> file) {
        if (file.size() > 1) {
            ragService.upload(file);
        } else {
            ragService.upload(file.get(0));
        }
        return R.ok();
    }

    /**
     * 显示rag上传文件列表
     *
     * @return
     */
    @GetMapping("/listFile")
    public R<List<RagFile>> listFile() {
        List<RagFile> list = ragService.listFile();
        return R.ok(list);
    }

    @GetMapping("/searchRagFile")
    public R<List<RagSearchVo>> searchRagFile(@RequestParam("msg")String msg) {
        List<RagSearchVo> result = ragService.searchRagFile(msg);

        return R.ok(result);
    }


}

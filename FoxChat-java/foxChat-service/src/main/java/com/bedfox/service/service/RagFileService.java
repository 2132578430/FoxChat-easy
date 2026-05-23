package com.bedfox.service.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.bedfox.pojo.domain.RagFile;

import java.util.List;

/**
* @author 21325
* @description 针对表【rag_file】的数据库操作Service
* @createDate 2026-03-15 14:16:24
*/
public interface RagFileService extends IService<RagFile> {

    List<RagFile> selectZombieFile();

}

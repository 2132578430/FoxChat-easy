package com.bedfox.service.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.bedfox.pojo.domain.RagFile;

import java.util.List;

/**
* @author 21325
* @description 针对表【rag_file】的数据库操作Mapper
* @createDate 2026-03-15 14:16:24
* @Entity com.bedfox.bedfoxchat.domain.RagFile
*/
public interface RagFileMapper extends BaseMapper<RagFile> {

    List<RagFile> selectZombieFile();
}





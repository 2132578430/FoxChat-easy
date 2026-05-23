package com.bedfox.service.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.bedfox.pojo.domain.RagFile;
import com.bedfox.service.mapper.RagFileMapper;
import com.bedfox.service.service.RagFileService;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;

import java.util.List;

/**
* @author 21325
* @description 针对表【rag_file】的数据库操作Service实现
* @createDate 2026-03-15 14:16:24
*/
@Service
public class RagFileServiceImpl extends ServiceImpl<RagFileMapper, RagFile>
    implements RagFileService{

    @Resource
    RagFileMapper ragFileMapper;

    @Override
    public List<RagFile> selectZombieFile() {
        return ragFileMapper.selectZombieFile();
    }
}





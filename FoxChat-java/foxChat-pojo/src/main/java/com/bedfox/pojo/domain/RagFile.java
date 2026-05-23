package com.bedfox.pojo.domain;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 
 * @TableName rag_file
 */
@TableName(value ="rag_file")
@Data
public class RagFile implements Serializable {
    /**
     * 
     */
    @TableId
    private String id;

    /**
     * 文件名
     */
    private String fileName;

    /**
     * 文件路径
     */
    private String filePath;

    /**
     * 保存用户ID
     */
    private String userId;

    /**
     * 0创建/1存入数据库/2读入rag
     */
    private Integer status;

    /**
     * 
     */
    private LocalDateTime createTime;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}
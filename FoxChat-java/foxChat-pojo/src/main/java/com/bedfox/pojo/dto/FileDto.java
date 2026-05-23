package com.bedfox.pojo.dto;

import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

/**
 * @author bedFox
 */
@Data
public class FileDto {
    MultipartFile file;
}

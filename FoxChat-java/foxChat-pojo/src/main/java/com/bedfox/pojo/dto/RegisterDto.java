package com.bedfox.pojo.dto;

import lombok.Data;

/**
 * @author bedFox
 */
@Data
public class RegisterDto {
    String nickname;
    String username;
    String password;
    String email;
    String code;
}

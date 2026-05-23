package com.bedfox.common.util;

import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

/**
 * @author bedFox
 * @date 2026/3/15 11:20
 */
@Component
public class EmailUtil {
    @Resource
    private JavaMailSender javaMailSender;

    @Value("${spring.mail.username}")
    private String fromEmail;

    public void sendCodeToUser(String email, String code) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(fromEmail);
        message.setTo(email);
        message.setSubject("BedFox-Chat 注册验证码");
        message.setText("您的注册验证码是：" + code + "，请在5分钟内使用，请勿泄露给他人。");
        javaMailSender.send(message);
    }
}

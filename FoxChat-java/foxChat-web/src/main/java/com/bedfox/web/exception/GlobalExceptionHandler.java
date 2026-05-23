package com.bedfox.web.exception;

import com.bedfox.common.constant.ResultStatusConstant;
import com.bedfox.common.exception.BusinessException;
import com.bedfox.common.util.R;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * @author bedFox
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public R<String> handleBusiness(BusinessException e) {
        log.error("业务异常处理器捕获到异常：{}", e.getMessage());
        ResultStatusConstant status = e.getStatus();
        return R.error(status.getCode(), status.getMsg());
    }

    @ExceptionHandler(Throwable.class)
    public R<String> handleGlobal(Throwable throwable) {
        log.error("全局异常处理器捕获到异常:", throwable);
        return R.error();
    }
}

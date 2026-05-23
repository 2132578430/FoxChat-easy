package com.bedfox.netty.handler;

import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * @author bedFox
 */
@Component
public class ChatHandlerFactory implements ApplicationContextAware {
    public static final Map<Integer, MsgHandler> beanMap = new HashMap<>();

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        Map<String, MsgHandler> beans = applicationContext.getBeansOfType(MsgHandler.class);
        beans.values().forEach(bean -> {
            beanMap.put(bean.getMsgType().getCode(), bean);
        });
    }

    public static MsgHandler getHandler(Integer code) {
        if (beanMap.containsKey(code)) {
            return beanMap.get(code);
        }
        return null;
    }

}

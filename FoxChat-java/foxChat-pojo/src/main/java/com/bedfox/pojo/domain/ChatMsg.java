package com.bedfox.pojo.domain;

import lombok.Data;

import java.time.LocalDateTime;

/**
 *
 * @TableName chat_msg
 */
@Data
public class ChatMsg {
    /**
     * ID
     */
    private String id;

    /**
     * 发送人id
     */
    private String sendUserId;

    /**
     * 接收人id
     */
    private String acceptUserId;

    /**
     * 消息内容
     */
    private String msg;

    /**
     * 是否已读
     */
    private Boolean signFlag;

    /**
     * 消息创建时间
     */
    private LocalDateTime createTime;

    @Override
    public boolean equals(Object that) {
        if (this == that) {
            return true;
        }
        if (that == null) {
            return false;
        }
        if (getClass() != that.getClass()) {
            return false;
        }
        ChatMsg other = (ChatMsg) that;
        return (this.getId() == null ? other.getId() == null : this.getId().equals(other.getId()))
            && (this.getSendUserId() == null ? other.getSendUserId() == null : this.getSendUserId().equals(other.getSendUserId()))
            && (this.getAcceptUserId() == null ? other.getAcceptUserId() == null : this.getAcceptUserId().equals(other.getAcceptUserId()))
            && (this.getMsg() == null ? other.getMsg() == null : this.getMsg().equals(other.getMsg()))
            && (this.getSignFlag() == null ? other.getSignFlag() == null : this.getSignFlag().equals(other.getSignFlag()))
            && (this.getCreateTime() == null ? other.getCreateTime() == null : this.getCreateTime().equals(other.getCreateTime()));
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((getId() == null) ? 0 : getId().hashCode());
        result = prime * result + ((getSendUserId() == null) ? 0 : getSendUserId().hashCode());
        result = prime * result + ((getAcceptUserId() == null) ? 0 : getAcceptUserId().hashCode());
        result = prime * result + ((getMsg() == null) ? 0 : getMsg().hashCode());
        result = prime * result + ((getSignFlag() == null) ? 0 : getSignFlag().hashCode());
        result = prime * result + ((getCreateTime() == null) ? 0 : getCreateTime().hashCode());
        return result;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(getClass().getSimpleName());
        sb.append(" [");
        sb.append("Hash = ").append(hashCode());
        sb.append(", id=").append(id);
        sb.append(", sendUserId=").append(sendUserId);
        sb.append(", acceptUserId=").append(acceptUserId);
        sb.append(", msg=").append(msg);
        sb.append(", signFlag=").append(signFlag);
        sb.append(", createTime=").append(createTime);
        sb.append("]");
        return sb.toString();
    }
}

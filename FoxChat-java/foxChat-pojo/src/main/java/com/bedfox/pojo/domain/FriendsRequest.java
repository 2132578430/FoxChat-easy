package com.bedfox.pojo.domain;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 
 * @TableName friends_request
 */
@Data
public class FriendsRequest {
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
     * 发送时间
     */
    private LocalDateTime requestDataTime;

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
        FriendsRequest other = (FriendsRequest) that;
        return (this.getId() == null ? other.getId() == null : this.getId().equals(other.getId()))
            && (this.getSendUserId() == null ? other.getSendUserId() == null : this.getSendUserId().equals(other.getSendUserId()))
            && (this.getAcceptUserId() == null ? other.getAcceptUserId() == null : this.getAcceptUserId().equals(other.getAcceptUserId()))
            && (this.getRequestDataTime() == null ? other.getRequestDataTime() == null : this.getRequestDataTime().equals(other.getRequestDataTime()));
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((getId() == null) ? 0 : getId().hashCode());
        result = prime * result + ((getSendUserId() == null) ? 0 : getSendUserId().hashCode());
        result = prime * result + ((getAcceptUserId() == null) ? 0 : getAcceptUserId().hashCode());
        result = prime * result + ((getRequestDataTime() == null) ? 0 : getRequestDataTime().hashCode());
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
        sb.append(", requestDataTime=").append(requestDataTime);
        sb.append("]");
        return sb.toString();
    }
}
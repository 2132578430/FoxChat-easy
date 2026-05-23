package com.bedfox.pojo.domain;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 
 * @TableName chat_group
 */
@Data
public class ChatGroup {
    /**
     * 群聊id
     */
    private String id;

    /**
     * 群聊名称
     */
    private String groupName;

    /**
     * 群主userId
     */
    private String ownerUserId;

    /**
     * 群聊头像
     */
    private String faceImage;

    /**
     * 
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
        ChatGroup other = (ChatGroup) that;
        return (this.getId() == null ? other.getId() == null : this.getId().equals(other.getId()))
            && (this.getGroupName() == null ? other.getGroupName() == null : this.getGroupName().equals(other.getGroupName()))
            && (this.getOwnerUserId() == null ? other.getOwnerUserId() == null : this.getOwnerUserId().equals(other.getOwnerUserId()))
            && (this.getFaceImage() == null ? other.getFaceImage() == null : this.getFaceImage().equals(other.getFaceImage()))
            && (this.getCreateTime() == null ? other.getCreateTime() == null : this.getCreateTime().equals(other.getCreateTime()));
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((getId() == null) ? 0 : getId().hashCode());
        result = prime * result + ((getGroupName() == null) ? 0 : getGroupName().hashCode());
        result = prime * result + ((getOwnerUserId() == null) ? 0 : getOwnerUserId().hashCode());
        result = prime * result + ((getFaceImage() == null) ? 0 : getFaceImage().hashCode());
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
        sb.append(", groupName=").append(groupName);
        sb.append(", ownerUserId=").append(ownerUserId);
        sb.append(", faceImage=").append(faceImage);
        sb.append(", createTime=").append(createTime);
        sb.append("]");
        return sb.toString();
    }
}
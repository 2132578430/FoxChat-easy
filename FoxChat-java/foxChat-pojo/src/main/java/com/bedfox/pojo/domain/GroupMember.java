package com.bedfox.pojo.domain;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 
 * @TableName group_member
 */
@Data
public class GroupMember {
    /**
     * 
     */
    private String id;

    /**
     * 
     */
    private String groupNickname;

    /**
     * 
     */
    private String userId;

    /**
     * 
     */
    private String groupId;

    /**
     * 1成员2群主
     */
    private Integer role;

    /**
     * 
     */
    private LocalDateTime joinTime;

    /**
     * 
     */
    private String lastAckMsgId;

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
        GroupMember other = (GroupMember) that;
        return (this.getId() == null ? other.getId() == null : this.getId().equals(other.getId()))
            && (this.getGroupNickname() == null ? other.getGroupNickname() == null : this.getGroupNickname().equals(other.getGroupNickname()))
            && (this.getUserId() == null ? other.getUserId() == null : this.getUserId().equals(other.getUserId()))
            && (this.getGroupId() == null ? other.getGroupId() == null : this.getGroupId().equals(other.getGroupId()))
            && (this.getRole() == null ? other.getRole() == null : this.getRole().equals(other.getRole()))
            && (this.getJoinTime() == null ? other.getJoinTime() == null : this.getJoinTime().equals(other.getJoinTime()))
            && (this.getLastAckMsgId() == null ? other.getLastAckMsgId() == null : this.getLastAckMsgId().equals(other.getLastAckMsgId()));
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((getId() == null) ? 0 : getId().hashCode());
        result = prime * result + ((getGroupNickname() == null) ? 0 : getGroupNickname().hashCode());
        result = prime * result + ((getUserId() == null) ? 0 : getUserId().hashCode());
        result = prime * result + ((getGroupId() == null) ? 0 : getGroupId().hashCode());
        result = prime * result + ((getRole() == null) ? 0 : getRole().hashCode());
        result = prime * result + ((getJoinTime() == null) ? 0 : getJoinTime().hashCode());
        result = prime * result + ((getLastAckMsgId() == null) ? 0 : getLastAckMsgId().hashCode());
        return result;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(getClass().getSimpleName());
        sb.append(" [");
        sb.append("Hash = ").append(hashCode());
        sb.append(", id=").append(id);
        sb.append(", groupNickname=").append(groupNickname);
        sb.append(", userId=").append(userId);
        sb.append(", groupId=").append(groupId);
        sb.append(", role=").append(role);
        sb.append(", joinTime=").append(joinTime);
        sb.append(", lastAckMsgId=").append(lastAckMsgId);
        sb.append("]");
        return sb.toString();
    }
}
import request from '@/utils/request';

// Update user profile
export function updateProfile(data) {
  return request.post('/user/update', data);
}

// Get user info
export function getUserInfo() {
  return request.get('/user/info');
}

// Upload avatar (for user profile)
export function uploadAvatar(formData) {
  return request.post('/user/updateAvatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}

// Get avatar url by userId
export function getAvatarUrl(userId) {
  return request.get('/user/avatar', {
    params: { userId }
  });
}

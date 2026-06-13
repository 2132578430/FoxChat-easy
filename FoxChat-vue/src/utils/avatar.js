import { OSS_BASE_URL } from '@/utils/config';

const defaultUserAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png';

/**
 * 处理头像 URL，将相对路径拼接 OSS_BASE_URL
 */
const resolveAvatarUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  const cleanUrl = url.startsWith('/') ? url.substring(1) : url;
  if (cleanUrl.startsWith('oss/')) {
    return `${OSS_BASE_URL.replace('/oss', '')}/${cleanUrl}`;
  }
  return `${OSS_BASE_URL}/${cleanUrl}`;
};

const emotionEmojiMap = {
  '开心': '😊',
  '快乐': '😊',
  'happy': '😊',
  '悲伤': '😢',
  '难过': '😢',
  'sad': '😢',
  '愤怒': '😠',
  '生气': '😠',
  'anger': '😠',
  'angry': '😠',
  '惊讶': '😲',
  'surprise': '😲',
  'surprised': '😲',
  '恐惧': '😨',
  '害怕': '😨',
  'fear': '😨',
  'fearful': '😨',
  '厌恶': '🤢',
  'disgust': '🤢',
  'disgusted': '🤢',
  'neutral': '😐',
  '平静': '😐'
};

const emotionToEmoji = (emotion) => {
  return emotionEmojiMap[emotion] || emotionEmojiMap[emotion?.toLowerCase()] || '😊';
};

export { defaultUserAvatar, resolveAvatarUrl, emotionEmojiMap, emotionToEmoji };

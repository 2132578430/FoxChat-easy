class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        lookup = set()
        n = len(s)
        max_len = 0
        l = 0
        cur_len = 0

        for r in range(n):
            while s[r] in lookup:
                lookup.remove(s[l])
                l += 1
                cur_len -= 1
            lookup.add(s[r])
            cur_len += 1
            max_len = max(cur_len, max_len)

        return max_len

if __name__ == '__main__':
    s = Solution()
    ans = s.lengthOfLongestSubstring("abcabcbb")

    print(ans)